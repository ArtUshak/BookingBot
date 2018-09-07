# -*- coding: utf-8 -*-
"""
Telegram bot for booking auditorium (see `README.md`).
"""
from datetime import datetime, timedelta
import logging
import re

import telebot
import telebot.types

import booking
from botsettings import *
from exceptions import (BotCommandException, BotBadDateFormat, BotNoAccess,
                        BotBadInput, BotTimeOccupied, BotTimePassed,
                        BotBookingNotFound, BotUsernameNotFound)


logger = logging.getLogger('bot')


def get_help(help_filename):
    """
    Loads content of help text file `help_filename` and returns it.
    """
    logger.info('Loading help text...')
    with open(help_filename, encoding='utf-8') as help_file:
        help_text = help_file.read()
    return help_text


def get_contactlist(contactlist_filename):
    """
    Loads content of contact list text file `help_filename` and
    returns it.
    """
    logger.info('Loading contact list...')
    with open(contactlist_filename, encoding='utf-8') \
            as contactlist_file:
        contactlist_text = contactlist_file.read()
    return contactlist_text


def get_token(filename):
    """
    Loads token from from first line of file `filename` and
    returns it, without leading and trailing whitespaces.
    """
    logger.info('Loading token...')
    with open(filename, encoding='utf-8') as token_file:
        token = token_file.readline().strip()
    return token


def get_proxy(filename):
    """
    Loads proxy URL from from first line of file `filename` and
    returns it, without leading and trailing whitespaces.
    """
    logger.info('Loading proxy data...')
    with open(filename, encoding='utf-8') as token_file:
        proxy = token_file.readline().strip().split(' ', 1)
    if len(proxy) < 2:
        return None
    else:
        return proxy


logger.info('Starting bot...')

message_help = get_help(help_file)
logger.info('Help message:\n' + message_help)

message_contact_list = get_contactlist(contactlist_file)
logger.info('Contact list:\n' + message_contact_list)

booking_db = booking.BookingDB(adminlist_file, data_file, whitelist_file,
                               user_data_file)

token = get_token(token_file)
logger.info('Token loaded')

proxy_data = get_proxy(proxy_file)
logger.info('Proxy data loaded')
if proxy_data is not None:
    telebot.apihelper.proxy = {
        proxy_data[0]: proxy_data[1]
    }

bot = telebot.TeleBot(token)

logger.info('Bot instance created')


def get_timedelta(seconds):
    """
    Returns `datetime.timedelta` object from the seconds number
    `seconds`.
    """
    return timedelta(days=seconds // 86400,
                     seconds=seconds % 86400)


def get_datetime(seconds):
    """
    Returns `datetime.datetime` object with the `seconds` seconds
    passed after `booking.TIME_AXIS` (1970-01-01 00:00).
    """
    return booking.TIME_AXIS + get_timedelta(seconds)


def get_error_message(exception, if_ok=None):
    """
    Returns error message based on exception `exception`.
    If `exception` is `None`, it returns `if_ok`. If it is `None` too,
    it returns default success message.
    """
    if exception is None:
        if if_ok is None:
            return message_operation_ok
        else:
            return if_ok
    elif isinstance(exception, BotBadDateFormat):
        return message_bad_date_format
    elif isinstance(exception, BotNoAccess):
        return message_no_access
    elif isinstance(exception, BotBadInput):
        return message_bad_input
    elif isinstance(exception, BotTimeOccupied):
        return message_time_occupied
    elif isinstance(exception, BotTimePassed):
        return message_time_passed
    elif isinstance(exception, BotBookingNotFound):
        return message_booking_not_found
    elif isinstance(exception, BotUsernameNotFound):
        return message_username_not_found
    else:
        return message_misc_error


def format_timetable(timetable_data):
    """
    Returns formatted timetable `timetable_data` as string.
    Timetable is given as a list of booking items.
    In resulting string each booking item should be placed on
    different line, with data about start and end time and
    description.
    """
    date_str = None
    result = message_timetable_header + '\n'
    for timetable_item in timetable_data:
        curr_date_str = get_datetime(timetable_item[0]).strftime('%Y-%m-%d')
        if date_str != curr_date_str:
            date_str = curr_date_str
            result += message_timetable_date_row.format(date_str)
            result += '\n'
        result += message_timetable_row.format(
            get_datetime(timetable_item[0]).strftime('%H:%M'),
            (get_datetime(timetable_item[0]
             + timetable_item[1]).strftime('%H:%M')),
            timetable_item[2]
        )
        result += '\n'
    return result


def format_whitelist(whitelist):
    """
    Returns formatted whitelist `whitelist` as string.
    Whitelist is given as a list of tuples of user IDs and usernames.
    In resulting string each user should be placed on
    different line.
    """
    result = message_whitelist_header + '\n'
    for whitelist_item in whitelist:
        result += message_whitelist_row.format(*whitelist_item)
        result += '\n'
    return result


def process_message_sender(message):
    """
    Processes `message`, updates user data and retuns user id from `message`.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    booking_db.update_user_data(user_id, chat_id, username)
    return user_id


inline_handlers = []


def inline_handler(pattern):
    def wrapper(func):
        inline_handlers.append((re.compile(pattern), func,))
        return func
    return wrapper


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    for handler in inline_handlers:
        match_result = handler[0].match(call.data)
        if match_result is not None:
            args = list(match_result.groups())
            args.append(call)
            handler[1](*args)
            return
    bot.send_message(call.message.chat.id, message_indev)


@inline_handler(r'help:(\d+)')
def process_button_help(sender_id, call):
    chat_id = call.message.chat.id
    keyboard = get_cmd_keyboard(chat_id)
    bot.send_message(chat_id, message_help, reply_markup=keyboard)


@bot.message_handler(commands=['start', 'help'])
def process_cmd_help(message):
    """
    Command `/help`
    Syntax: `/help`
    Syntax: `/start`
    Displays help text message.
    """
    chat_id = message.chat.id
    keyboard = get_cmd_keyboard(chat_id)
    bot.send_message(chat_id, message_help, reply_markup=keyboard)


def get_cmd_keyboard(chat_id):
    """
    Creates inline keyboard for bot functions and returns it.
    Requires parameter `chat_id`.
    """
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable,
            callback_data='timetable:{}'.format(str(chat_id))))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_today,
            callback_data='timetable_today:{}'.format(str(chat_id))))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_today,
            callback_data='timetable_date:{}'.format(str(chat_id))))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_book,
            callback_data='book:{}'.format(str(chat_id))))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_unbook,
            callback_data='unbook:{}'.format(str(chat_id))))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_contactlist,
            callback_data='contactlist:{}'.format(str(chat_id))))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_help,
            callback_data='help:{}'.format(str(chat_id))))
    return keyboard


@bot.message_handler(commands=['book'])
def process_cmd_book(message):
    """
    Command `/book`
    Syntax: `/book <DATE> <TIME> <DURATION> <DESCRIPTION>`
    Adds new booking item starting from moment `<DATE> <TIME>` and
    ending at moment `<DATE> <TIME> + <DURATION>` with description
    `<DESCRIPTION>`.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /book from user {} ({})'.format(sender_id,
                                                message.from_user.username))
    exc = None
    try:
        if len(message.text.split()) < 5:
            raise BotBadInput()
        words = message.text.split(' ', 4)
        date_str = words[1]
        time_str = words[2]
        duration_str = words[3]
        description = words[4]
        log_msg_format = ('Called /book for date {}, time {}, duration {}, '
                          'description {}')
        logger.info(
            log_msg_format.format(
                date_str, time_str, duration_str, description))
        try:
            time = booking.process_date_time(date_str, time_str)
            duration = booking.process_time(duration_str)
        except ValueError:
            raise BotBadInput()
        else:
            booking_db.book(sender_id, time, duration, description)
        booking_db.save_all_data(-1, data_file, whitelist_file,
                                 user_data_file)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /book')
            raise
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['unbook'])
def process_cmd_unbook(message):
    """
    Command `/unbook`
    Syntax: `/unbook <DATE> <TIME>`
    Removes booking that intersect with moment `<DATE> <TIME>`. Does not
    remove booking if it was not added by current user or if it has
    passed.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /unbook from user {} ({})'.format(sender_id,
                                                  message.from_user.username))
    exc = None
    try:
        if len(message.text.split()) < 3:
            raise BotBadInput()
        words = message.text.split(' ', 3)
        date_str = words[1]
        time_str = words[2]
        logger.info(
            'Called /unbook for date {}, time {}'.format(date_str, time_str))
        try:
            time = booking.process_date_time(date_str, time_str)
        except ValueError:
            raise BotBadInput()
        else:
            booking_db.unbook(sender_id, time)
        booking_db.save_all_data(-1, data_file, whitelist_file,
                                 user_data_file)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /unbook')
            raise
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['unbook_force'])
def process_cmd_unbook_force(message):
    """
    Command `/unbook_force`
    Syntax: `/unbook <DATE> <TIME>`
    Removes booking that intersect with moment `<DATE> <TIME>` without
    restrictions applied `/unbook` command, although still respecting
    user permissions.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /unbook_force from user {} ({})'.format(
            sender_id, message.from_user.username))
    exc = None
    try:
        if len(message.text.split()) < 3:
            raise BotBadInput()
        words = message.text.split(' ', 3)
        date_str = words[1]
        time_str = words[2]
        logger.info(
            'Called /unbook_force for date {}, time {}'.format(
                date_str, time_str))
        try:
            time = booking.process_date_time(date_str, time_str)
        except ValueError:
            raise BotBadInput()
        else:
            booking_db.unbook(sender_id, time, force=True)
        booking_db.save_all_data(-1, data_file, whitelist_file,
                                 user_data_file)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /unbook_force')
            raise
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@inline_handler(r'timetable:(\d+)')
def process_button_timetable(sender_id, call):
    chat_id = call.message.chat.id
    logger.info('Called /timetable from user {}'.format(sender_id))
    exc = None
    timetable = []
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
    end_time = -1
    try:
        cmd_result_list = booking_db.get_timetable(sender_id, start_time,
                                                   end_time)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /timetable')
            raise
        exc = exception
    else:
        timetable = format_timetable(cmd_result_list)
    keyboard = get_cmd_keyboard(chat_id)
    bot.send_message(chat_id, get_error_message(exc, if_ok=timetable),
                     reply_markup=keyboard)


@inline_handler(r'timetable_today:(\d+)')
def process_button_timetable_today(sender_id, call):
    chat_id = call.message.chat.id
    logger.info('Called /timetable from user {}'.format(sender_id))
    exc = None
    timetable = []
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
    end_time = start_time + 86400
    try:
        cmd_result_list = booking_db.get_timetable(sender_id, start_time,
                                                   end_time)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /timetable')
            raise
        exc = exception
    else:
        timetable = format_timetable(cmd_result_list)
    keyboard = get_cmd_keyboard(chat_id)
    bot.send_message(chat_id, get_error_message(exc, if_ok=timetable),
                     reply_markup=keyboard)


@bot.message_handler(commands=['timetable'])
def process_cmd_timetable(message):
    """
    Command `/timetable`
    Syntax: `/timetable`
    Syntax: `/timetable TODAY`
    Syntax: `/timetable <DATE>`
    Displays timetable for all timeline since current day (if no
    parameters were given), for current day (if parameter was TODAY)
    or for `<DATE>` (if it was given).
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /timetable from user {} ({})'.format(
            sender_id,
            message.from_user.username))
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
    end_time = -1
    exc = None
    timetable = []
    try:
        if len(message.text.split()) >= 2:
            words = message.text.split(' ', 2)
            if words[1].lower() == 'today':
                end_time = (
                    (datetime.today() - booking.TIME_AXIS).total_seconds()
                    + 86400)
            else:
                try:
                    start_time = booking.process_date(words[1])
                    end_time = start_time + 86400
                except ValueError:
                    raise BotBadDateFormat()
        cmd_result_list = booking_db.get_timetable(sender_id, start_time,
                                                   end_time)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /timetable')
            raise
        exc = exception
    else:
        timetable = format_timetable(cmd_result_list)
    bot.send_message(message.chat.id, get_error_message(exc,
                                                        if_ok=timetable))
    booking_db.save_whitelist(whitelist_file)


@bot.message_handler(commands=['savedata'])
def process_cmd_save(message):
    """
    Command `/savedata`
    Syntax: `/savedata`
    Saves current booking data and white list to files.
    This command is administrator-only.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /savedata from user {} ({})'.format(
            sender_id, message.from_user.username))
    exc = None
    try:
        booking_db.save_all_data(sender_id, data_file, whitelist_file,
                                 user_data_file)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /savedata')
            raise
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['logmyinfo'])
def process_cmd_logmyinfo(message):
    """
    Command `/logmyinfo`
    Syntax: `/logmyinfo`
    Does nothing, just writes user ID and username to log.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /logmyinfo from user {} ({})'.format(
            sender_id, message.from_user.username))
    booking_db.save_whitelist(whitelist_file)


@inline_handler(r'contactlist:(\d+)')
def process_button_contactlist(sender_id, call):
    chat_id = call.message.chat.id
    keyboard = get_cmd_keyboard(chat_id)
    bot.send_message(chat_id, message_contact_list, reply_markup=keyboard)


@bot.message_handler(commands=['contactlist'])
def process_cmd_contactlist(message):
    bot.send_message(message.chat.id, message_contact_list)


@bot.message_handler(commands=['whitelist'])
def process_cmd_whitelist(message):
    """
    Command `/whitelist`
    Syntax: `/whitelist`
    Syntax: `/whitelist ADD <USERNAME>`
    Syntax: `/whitelist REMOVE <USERNAME>`
    Displays current whitelist (if no parameters were given) or
    adds user `<USERNAME>` or removes him from whitelist.
    This command is administrator-only.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /whitelist from user {} ({})'.format(
            sender_id,
            message.from_user.username))
    exc = None
    msg_text = None
    try:
        if len(message.text.split()) == 1:
            whitelist = booking_db.get_whitelist(sender_id)
            msg_text = format_whitelist(whitelist)
        elif len(message.text.split()) == 3:
            words = message.text.split(' ', 3)
            action_str = words[1].lower()
            username = words[2]
            if action_str == 'add':
                booking_db.add_user_to_whitelist(sender_id, username)
            elif action_str == 'remove':
                booking_db.remove_user_from_whitelist(sender_id, username)
            else:
                raise BotBadInput()
        else:
            raise BotBadInput()
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /timetable')
            raise
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc,
                                                        if_ok=msg_text))
    booking_db.save_whitelist(whitelist_file)


'''
@bot.message_handler(content_types=['text'])
def process_input(message):
    log(message.text)
    words = message.text.split()
    log(str(words))
    if len(words) != 2:
        bot.send_message(message.chat.id, message_bad_input)
    else:
        name = words[0]
        lang = words[1]
        if result == None:
            bot.send_message(message.chat.id, '!')
        #else:
            #bot.send_message(message.chat.id, message_output % result)
'''


if __name__ == '__main__':
    logger.info('Started polling')
    bot.polling()
