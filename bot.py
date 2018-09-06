# -*- coding: utf-8 -*-
"""
Telegram bot for booking auditorium (see `README.md`).
"""
from datetime import datetime, timedelta
import logging

import telebot
import telebot.types

import booking
from botsettings import *
from exceptions import (BotCommandException, BotBadDateFormat, BotNoAccess,
                        BotBadInput, BotTimeOccupied, BotTimePassed,
                        BotBookingNotFound)


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


logger.info('Starting bot...')

message_help = get_help(help_file)
logger.info('Help message:\n' + message_help)

message_contact_list = get_contactlist(contactlist_file)
logger.info('Contact list:\n' + message_contact_list)

booking_db = booking.BookingDB(adminlist_file, data_file, whitelist_file)

token = get_token(token_file)
logger.info('Token loaded')

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


@bot.message_handler(commands=['start', 'help'])
def process_cmd_help(message):
    """
    Command `/help`
    Syntax: `/help`
    Syntax: `/start`
    Displays help text message.
    """
    bot.send_message(message.chat.id, message_help)
    # send_cmd_keyboard(message.chat.id, message_testing)


def send_cmd_keyboard(chat_id, text):
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
    bot.send_message(chat_id, text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    tokens = call.data.split(':')
    if len(tokens) < 2:
        return
    if tokens[0] == 'timetable':
        process_button_timetable(int(tokens[1]), call.message.chat.id)
    if tokens[0] == 'contactlist':
        process_button_contactlist(int(tokens[1]), call.message.chat.id)
    else:
        bot.send_message(message_indev, call.message.chat.id)


@bot.message_handler(commands=['book'])
def process_cmd_book(message):
    """
    Command `/book`
    Syntax: `/book <DATE> <TIME> <DURATION> <DESCRIPTION>`
    Adds new booking item starting from moment `<DATE> <TIME>` and
    ending at moment `<DATE> <TIME> + <DURATION>` with description
    `<DESCRIPTION>`.
    """
    sender_id = message.from_user.id
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
    sender_id = message.from_user.id
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
    sender_id = message.from_user.id
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
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /unbook_force')
            raise
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


def process_button_timetable(sender_id, chat_id):
    logger.info('Called /timetable from user {}'.format(sender_id))
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
    end_time = -1
    exc = None
    timetable = []
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
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
    bot.send_message(chat_id, get_error_message(exc, if_ok=timetable))


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
    sender_id = message.from_user.id
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


@bot.message_handler(commands=['savedata'])
def process_cmd_save(message):
    """
    Command `/savedata`
    Syntax: `/savedata`
    Saves current booking data and white list to files.
    This command is administrator-only.
    """
    sender_id = message.from_user.id
    logger.info(
        'Called /savedata from user {} ({})'.format(
            sender_id, message.from_user.username))
    exc = None
    try:
        booking_db.save_all_data(sender_id, data_file, whitelist_file)
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
    sender_id = message.from_user.id
    logger.info(
        'Called /logmyinfo from user {} ({})'.format(
            sender_id, message.from_user.username))


def process_button_contactlist(sender_id, chat_id):
    bot.send_message(chat_id, message_contact_list)


@bot.message_handler(commands=['contactlist'])
def process_cmd_contactlist(message):
    bot.send_message(message.chat.id, message_contact_list)


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
