# -*- coding: utf-8 -*-
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
    logger.info('Loading help text...')
    with open(help_filename, encoding='utf-8') as help_file:
        help_text = help_file.read()
    return help_text


def get_contactlist(contactlist_filename):
    logger.info('Loading contact list...')
    with open(contactlist_filename, encoding='utf-8') \
            as contactlist_file:
        contactlist_text = contactlist_file.read()
    return contactlist_text


def get_token(filename):
    logger.info('Loading token...')
    with open(filename, encoding='utf-8') as token_file:
        token = token_file.readline().strip()
    return token


logger.info('Starting bot...')

message_help = get_help(help_file)
logger.info('Help message:\n' + message_help)

message_contact_list = get_contactlist(contactlist_file)
logger.info('Contact list:\n' + message_contact_list)

booking.load_data(data_file)
logger.info('Data loaded')

booking.load_whitelist(whitelist_file)
logger.info('Whitelist loaded')
logger.info('Whitelist: {}'.format(str(booking.whitelist)))

booking.load_admins(adminlist_file)
logger.info('Admin list loaded')
logger.info('Admins: {}'.format(str(booking.admins)))

token = get_token(token_file)

bot = telebot.TeleBot(token)

logger.info('Bot instance created')


def get_timedelta(seconds):
    return timedelta(days=seconds // 86400,
                     seconds=seconds % 86400)


def get_datetime(seconds):
    return booking.TIME_AXIS + get_timedelta(seconds)


def get_error_message(exception, if_ok=None):
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
    date_str = None
    result = message_timetable_header + '\n'
    for timetable_item in timetable_data:
        curr_date_str = get_datetime(timetable_item[0]).strftime('%Y-%m-%d')
        if date_str != curr_date_str:
            date_str = curr_date_str
            result += message_timetable_date_row.format(date_str)
            result += '\n'
        result += message_timetable_row.format(
            (get_datetime(timetable_item[0]).strftime('%H:%M'),
             get_datetime(timetable_item[0]
             + timetable_item[1]).strftime('%H:%M'),
             timetable_item[2])
        )
        result += '\n'
    return result


# TODO
"""
@bot.message_handler(commands=['start', 'help'])
def process_cmd_help(message):
    bot.send_message(message.chat.id, message_help)
    send_cmd_keyboard(message.chat.id, message_testing)
"""


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


@bot.message_handler(commands=['book'])
def process_cmd_book(message):
    sender_id = message.from_user.id
    logger.info(
        'Called /book from user {} ({})'.format(sender_id,
                                                message.from_user.username))
    if len(message.text.split()) < 5:
        bot.send_message(message.chat.id, message_bad_input)
        return
    words = message.text.split(' ', 5)
    exc = None
    try:
        log_msg_format = ('Called /book for date {}, time {}, duration {}, '
                          'description {}')
        logger.info(
            log_msg_format.format(
                words[1], words[2], words[3], words[4]))
        try:
            time = booking.process_date_time(words[1], words[2])
            duration = booking.process_time(words[3])
        except ValueError:
            raise BotBadInput()
        else:
            booking.book(sender_id, time, duration, words[4])
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /book')
            logger.exception(exception)
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['unbook'])
def process_cmd_unbook(message):
    sender_id = message.from_user.id
    logger.info(
        'Called /unbook from user {} ({})'.format(sender_id,
                                                  message.from_user.username))
    if len(message.text.split()) < 3:
        bot.send_message(message.chat.id, message_bad_input)
        return
    words = message.text.split(' ', 3)
    exc = None
    try:
        logger.info(
            'Called /unbook for date {}, time {}'.format(words[1], words[2]))
        try:
            time = booking.process_date_time(words[1], words[2])
        except ValueError:
            raise BotBadInput()
        else:
            booking.unbook(sender_id, time)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /unbook')
            logger.exception(exception)
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['unbook_force'])
def process_cmd_unbook_force(message):
    sender_id = message.from_user.id
    logger.info(
        'Called /unbook_force from user {} ({})'.format(
            sender_id,
            message.from_user.username))
    if len(message.text.split()) < 3:
        bot.send_message(message.chat.id, message_bad_input)
        return
    words = message.text.split(' ', 3)
    exc = None
    try:
        logger.info(
            'Called /unbook_force for date {}, time {}'.format(words[1],
                                                               words[2]))
        try:
            time = booking.process_date_time(words[1], words[2])
        except ValueError:
            raise BotBadInput
        else:
            booking.unbook(sender_id, time, force=True)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /unbook_force')
            logger.exception(exception)
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
        cmd_result_list = booking.get_timetable(sender_id, start_time,
                                                end_time)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /timetable')
            logger.exception(exception)
        exc = exception
    else:
        timetable = format_timetable(cmd_result_list[1:])
    bot.send_message(chat_id, get_error_message(exc, if_ok=timetable))


@bot.message_handler(commands=['timetable'])
def process_cmd_timetable(message):
    sender_id = message.from_user.id
    logger.info(
        'Called /timetable from user {} ({})'.format(
            sender_id,
            message.from_user.username))
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
    end_time = -1
    if len(message.text.split()) >= 2:
        words = message.text.split(' ', 2)
        if words[1].lower() == 'today':
            end_time = (datetime.today() - booking.TIME_AXIS).total_seconds() \
                       + 86400
    exc = None
    timetable = []
    start_time = (datetime.today() - booking.TIME_AXIS).total_seconds()
    try:
        cmd_result_list = booking.get_timetable(sender_id, start_time,
                                                end_time)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /timetable')
            logger.exception(exception)
        exc = exception
    else:
        timetable = format_timetable(cmd_result_list[1:])
    bot.send_message(message.chat.id, get_error_message(exc,
                                                        if_ok=timetable))


@bot.message_handler(commands=['savedata'])
def process_cmd_save(message):
    sender_id = message.from_user.id
    logger.info(
        'Called /savedata from user {} ({})'.format(
            sender_id, message.from_user.username))
    exc = None
    try:
        booking.save_all_data(sender_id, data_file, whitelist_file)
    except Exception as exception:
        if not isinstance(exception, BotCommandException):
            logger.error('Error ocurred when executing comand /saveadata')
            logger.exception(exception)
        exc = exception
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['logmyinfo'])
def process_cmd_logmyinfo(message):
    sender_id = message.from_user.id
    logger.info(
        'Called /logmyinfo from user {} ({})'.format(
            sender_id, message.from_user.username))


def process_button_contactlist(sender_id, chat_id):
    bot.send_message(chat_id, message_contact_list)


@bot.message_handler(commands=['contactlist'])
def process_cmd_contactlist(message):
    bot.send_message(message.chat.id, message_contact_list)


@bot.message_handler(commands=['help'])
def process_cmd_help(message):
    bot.send_message(message.chat.id, message_help)


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
    bot.polling()
