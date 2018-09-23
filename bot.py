# -*- coding: utf-8 -*-
"""Telegram bot for booking auditorium (see `README.md`)."""
import calendar
import datetime
import logging
import re

import telebot
import telebot.types

import booking
from botsettings import (message_indev, message_operation_ok,
                         message_bad_input, message_bad_date_format,
                         message_no_access, message_misc_error,
                         message_time_occupied, message_time_passed,
                         message_booking_not_found, message_username_not_found,
                         message_timetable_header, message_timetable_date_row,
                         message_timetable_row, message_whitelist_header,
                         message_whitelist_row,
                         cmd_text_timetable, cmd_text_timetable_today,
                         cmd_text_timetable_date,
                         cmd_text_timetable_book, cmd_text_timetable_unbook,
                         cmd_text_contactlist, cmd_text_help,
                         message_timetable_date_0, message_book_0,
                         message_book_1, message_book_2, message_book_3,
                         contactlist_file, help_file, data_file,
                         whitelist_file, adminlist_file, token_file,
                         proxy_file, user_data_file)
from exceptions import (BotCommandException, BotBadDateFormat, BotNoAccess,
                        BotBadInput, BotTimeOccupied, BotTimePassed,
                        BotBookingNotFound, BotUsernameNotFound)


logger = logging.getLogger('bot')


def get_help(help_filename):
    """
    Load help text.

    Load content of help text file `help_filename` and return it.
    """
    logger.info('Loading help text...')
    with open(help_filename, encoding='utf-8') as help_file:
        help_text = help_file.read()
    return help_text


def get_contactlist(contactlist_filename):
    """
    Load contact list text.

    Load content of contact list text file `help_filename` and
    return it.
    """
    logger.info('Loading contact list...')
    with open(contactlist_filename, encoding='utf-8') \
            as contactlist_file:
        contactlist_text = contactlist_file.read()
    return contactlist_text


def get_token(filename):
    """
    Load token.

    Load token from from first line of file `filename` and
    return it, without leading and trailing whitespaces.
    """
    logger.info('Loading token...')
    with open(filename, encoding='utf-8') as token_file:
        token = token_file.readline().strip()
    return token


def get_proxy(filename):
    """
    Load proxy URL.

    Load proxy URL from from first line of file `filename` and
    return it, without leading and trailing whitespaces.
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


def get_error_message(exception, if_ok=None):
    """
    Return error message based on exception `exception`.

    If `exception` is `None`, it return `if_ok`. If it is `None` too,
    it return default success message.
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
    Return formatted timetable `timetable_data` as string.

    Timetable is given as a list of booking items.
    In resulting string each booking item should be placed on
    different line, with data about start and end time and
    description.
    """
    # TODO: probably split timetable messages using telebot.util.split_string()
    date_str = None
    result = message_timetable_header + '\n'
    for timetable_item in timetable_data:
        curr_date_str = timetable_item[0].strftime('%Y-%m-%d')
        if date_str != curr_date_str:
            date_str = curr_date_str
            result += message_timetable_date_row.format(date_str)
            result += '\n'
        result += message_timetable_row.format(
            timetable_item[0].strftime('%H:%M'),
            ((timetable_item[0] + timetable_item[1]).strftime('%H:%M')),
            timetable_item[2]
        )
        result += '\n'
    return result


def format_whitelist(whitelist):
    """
    Return formatted whitelist `whitelist` as string.

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
    Process message and update user data.

    Process `message`, update user data and return user id from `message`.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    booking_db.update_user_data(user_id, chat_id, username)
    return user_id


@bot.callback_query_handler(func=lambda call: call.data == 'help')
def process_button_help(call):
    """
    Button `help`.

    Display help text message.
    """
    chat_id = call.message.chat.id
    keyboard = get_cmd_keyboard()
    bot.send_message(chat_id, message_help, reply_markup=keyboard)
    bot.answer_callback_query(call.id, text='')


@bot.message_handler(commands=['start', 'help'])
def process_cmd_help(message):
    """
    Command `/help`.

    Syntax: `/help`
    Syntax: `/start`
    Display help text message.
    """
    process_message_sender(message)
    booking_db.save_user_data(user_data_file)
    keyboard = get_cmd_keyboard()
    bot.send_message(message.chat.id, message_help, reply_markup=keyboard)


# Taken from https://github.com/unmonoqueteclea/calendar-telegram
def get_calendar(year, month):
    """
    Create inline keyboard for calendar and return it.

    Calendar will be created for `year` and `month`.
    """
    markup = telebot.types.InlineKeyboardMarkup()

    # First row - Month and Year
    row = []
    row.append(
        telebot.types.InlineKeyboardButton(
            calendar.month_name[month] + ' ' + str(year),
            callback_data='ignore'))
    markup.row(*row)

    # Second row - Week Days
    week_days = list(map(lambda day_name: day_name[0], calendar.day_name))
    row = []
    for day in week_days:
        row.append(telebot.types.InlineKeyboardButton(
            day, callback_data='ignore'))
    markup.row(*row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(telebot.types.InlineKeyboardButton(
                    ' ', callback_data='ignore'))
            else:
                row.append(telebot.types.InlineKeyboardButton(
                    str(day), callback_data='calendar_day:{}'.format(day)))
        markup.row(*row)

    # Last row - Buttons
    row = []
    row.append(telebot.types.InlineKeyboardButton(
        '<', callback_data='previous_month'))
    row.append(telebot.types.InlineKeyboardButton(
        ' ', callback_data='ignore'))
    row.append(telebot.types.InlineKeyboardButton(
        '>', callback_data='next_month'))
    markup.row(*row)
    return markup


def get_cmd_keyboard():
    """Create inline keyboard for bot functions and return it."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable,
            callback_data='timetable'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_today,
            callback_data='timetable_today'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_date,
            callback_data='timetable_date'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_book,
            callback_data='book'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_timetable_unbook,
            callback_data='unbook'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_contactlist,
            callback_data='contactlist'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            text=cmd_text_help,
            callback_data='help'))
    return keyboard


@bot.callback_query_handler(func=lambda call: call.data == 'book')
def process_button_book(call):
    """
    Button `book`.

    Start input to add new booking item.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    logger.info('Called button book from user {}'.format(
        sender.user_id))
    exc = None
    try:
        sender.start_input_line('book')
        booking_db.save_user_data(user_data_file)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing button book')
        raise
    bot.send_message(
        chat_id, get_error_message(exc, if_ok=message_book_0),
        reply_markup=get_calendar(sender.input_date_year,
                                  sender.input_date_month))
    bot.answer_callback_query(call.id, text='')


@bot.message_handler(commands=['book'])
def process_cmd_book(message):
    """
    Command `/book`.

    Syntax: `/book <DATE> <TIME> <DURATION> <DESCRIPTION>`
    Add new booking item starting from moment `<DATE> <TIME>` and
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
            duration = booking.process_timedelta(duration_str)
        except ValueError:
            raise BotBadInput()
        else:
            booking_db.book(sender_id, time, duration, description)
        booking_db.save_all_data(-1, data_file, whitelist_file,
                                 user_data_file)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing command')
        raise
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['unbook'])
def process_cmd_unbook(message):
    """
    Command `/unbook`.

    Syntax: `/unbook <DATE> <TIME>`
    Remove booking that intersect with moment `<DATE> <TIME>`. Do not
    remove booking if it was not added by current user or if it has
    already passed.
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
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing command')
        raise
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['unbook_force'])
def process_cmd_unbook_force(message):
    """
    Command `/unbook_force`.

    Syntax: `/unbook <DATE> <TIME>`
    Remove booking that intersect with moment `<DATE> <TIME>` without
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
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing command')
        raise
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.callback_query_handler(func=lambda call: call.data == 'timetable')
def process_button_timetable(call):
    """
    Button `timetable`.

    Display timetable for all timeline since current day.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    logger.info('Called button timetable from {}'.format(sender.user_id))
    exc = None
    timetable = None
    start_time = datetime.datetime.today()
    end_time = None
    try:
        cmd_result = booking_db.get_timetable(sender.user_id, start_time,
                                              end_time)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing button timetable')
        raise
    else:
        timetable = format_timetable(cmd_result)
    keyboard = get_cmd_keyboard()
    bot.send_message(chat_id, get_error_message(exc, if_ok=timetable),
                     reply_markup=keyboard)
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(func=lambda call: call.data == 'timetable_today')
def process_button_timetable_today(call):
    """
    Button `timetable_today`.

    Display timetable for current day.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    logger.info('Called button timetable_today from user {}'.format(
        sender.user_id))
    exc = None
    timetable = []
    start_time = datetime.datetime.today()
    end_time = start_time + datetime.timedelta(days=1)
    try:
        cmd_result = booking_db.get_timetable(sender.user_id, start_time,
                                              end_time)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing button timetable_today')
        raise
    else:
        timetable = format_timetable(cmd_result)
    keyboard = get_cmd_keyboard()
    bot.send_message(chat_id, get_error_message(exc, if_ok=timetable),
                     reply_markup=keyboard)
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(func=lambda call: call.data == 'timetable_date')
def process_button_timetable_date(call):
    """
    Button `timetable_date`.

    Start inputting data to display timetable for given day.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    logger.info('Called button timetable_date from user {}'.format(
        sender.user_id))
    exc = None
    try:
        sender.start_input_line('timetable_date')
        booking_db.save_user_data(user_data_file)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing button timetable_date')
        raise
    bot.send_message(
        chat_id, get_error_message(exc, if_ok=message_timetable_date_0),
        reply_markup=get_calendar(sender.input_date_year,
                                  sender.input_date_month))
    bot.answer_callback_query(call.id, text='')


@bot.message_handler(commands=['timetable'])
def process_cmd_timetable(message):
    """
    Command `/timetable`.

    Syntax: `/timetable`
    Syntax: `/timetable TODAY`
    Syntax: `/timetable <DATE>`
    Display timetable for all timeline since current day (if no
    parameters were given), for current day (if parameter was TODAY)
    or for `<DATE>` (if it was given).
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /timetable from user {} ({})'.format(
            sender_id,
            message.from_user.username))
    start_time = datetime.datetime.today()
    end_time = None
    exc = None
    timetable = []
    try:
        if len(message.text.split()) >= 2:
            words = message.text.split(' ', 2)
            if words[1].lower() == 'today':
                end_time = (datetime.datetime.today()
                            + datetime.timedelta(days=1))
            else:
                try:
                    start_date = booking.process_date(words[1])
                except ValueError:
                    raise BotBadDateFormat()
                start_time = datetime.datetime.combine(start_date,
                                                       datetime.time.min)
                end_time = start_time + datetime.timedelta(days=1)
        cmd_result = booking_db.get_timetable(sender_id, start_time, end_time)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing command')
        raise
    else:
        timetable = format_timetable(cmd_result)
    bot.send_message(message.chat.id, get_error_message(exc,
                                                        if_ok=timetable))
    booking_db.save_user_data(user_data_file)


@bot.message_handler(commands=['savedata'])
def process_cmd_save(message):
    """
    Command `/savedata`.

    Syntax: `/savedata`
    Save current booking data and white list to files.
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
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing command')
        raise
    bot.send_message(message.chat.id, get_error_message(exc))


@bot.message_handler(commands=['logmyinfo'])
def process_cmd_logmyinfo(message):
    """
    Command `/logmyinfo`.

    Syntax: `/logmyinfo`
    Do nothing, just write user ID and username to log.
    """
    sender_id = process_message_sender(message)
    logger.info(
        'Called /logmyinfo from user {} ({})'.format(
            sender_id, message.from_user.username))
    booking_db.save_user_data(user_data_file)


@bot.callback_query_handler(func=lambda call: call.data == 'contactlist')
def process_button_contactlist(call):
    """
    Button `contactlist`.

    Display contact list text message.
    """
    chat_id = call.message.chat.id
    keyboard = get_cmd_keyboard()
    bot.send_message(chat_id, message_contact_list, reply_markup=keyboard)
    bot.answer_callback_query(call.id, text='')


@bot.message_handler(commands=['contactlist'])
def process_cmd_contactlist(message):
    """
    Command `/contactlist`.

    Syntax: `/contactlist`
    Display contact list text message.
    """
    bot.send_message(message.chat.id, message_contact_list)


@bot.message_handler(commands=['whitelist'])
def process_cmd_whitelist(message):
    """
    Command `/whitelist`.

    Syntax: `/whitelist`
    Syntax: `/whitelist ADD <USERNAME>`
    Syntax: `/whitelist REMOVE <USERNAME>`
    Display current whitelist (if no parameters were given) or
    add user `<USERNAME>` or remove him from whitelist.
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
        booking_db.save_all_data(-1, data_file, whitelist_file, user_data_file)
    except BotCommandException as exception:
        exc = exception
    except Exception:
        logger.error('Error ocurred when executing command')
        raise
    bot.send_message(message.chat.id, get_error_message(exc,
                                                        if_ok=msg_text))


@bot.callback_query_handler(func=lambda call: call.data == 'next_month')
def process_button_next_month(call):
    """
    Button `next_month`.

    Change to next month if calendar is shown.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    if not sender.input_date:
        return
    logger.info('Called button next_month from user {}'.format(
        sender.user_id))
    exc = None
    try:
        sender.start_input_line('timetable_date')
        sender.input_date_next_month()
        booking_db.save_user_data(user_data_file)
    except BotCommandException as exception:
        exc = exception
        sender.start_input_line(None)
    except Exception:
        logger.error('Error ocurred when executing button next_month')
        raise
    bot.edit_message_text(
        get_error_message(exc, if_ok=message_timetable_date_0),
        call.from_user.id, call.message.message_id,
        reply_markup=get_calendar(sender.input_date_year,
                                  sender.input_date_month))
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(func=lambda call: call.data == 'previous_month')
def process_button_previous_month(call):
    """
    Button `previous_month`.

    Change to previous month if calendar is shown.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    if not sender.input_date:
        return
    logger.info('Called button previous_month from user {}'.format(
        sender.user_id))
    exc = None
    try:
        sender.start_input_line('timetable_date')
        sender.input_date_previous_month()
        booking_db.save_user_data(user_data_file)
    except BotCommandException as exception:
        exc = exception
        sender.start_input_line(None)
    except Exception:
        logger.error('Error ocurred when executing button previous_month')
        raise
    bot.edit_message_text(
        get_error_message(exc, if_ok=message_timetable_date_0),
        call.from_user.id, call.message.message_id,
        reply_markup=get_calendar(sender.input_date_year,
                                  sender.input_date_month))
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(func=lambda call: call.data == 'ignore')
def process_button_ignore(call):
    """
    Button `ignore`.

    Ignore button input, only mark it as answered.
    """
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('calendar_day:'))
def process_button_calendar_day(call):
    """
    Button `calendar_day:<DAY>`.

    Process calendar input of day `<DAY>`.
    """
    chat_id = call.message.chat.id
    sender = booking_db.get_user_by_chat_id(chat_id)
    if sender is None:
        return
    if not sender.input_date:
        return

    msg_text = None
    exc = None
    markup = get_cmd_keyboard()
    try:
        regex_match = re.match(r'calendar_day:([0-9]+)', call.data)
        if regex_match is None:
            raise BotBadInput()
        day = int(regex_match.group(1))
        logger.info('Called button calendar_day:{} from user {}'.format(
            day, sender.user_id))

        if ((sender.input_line_type != 'timetable_date')
                and (sender.input_line_type != 'book')):
            raise BotBadInput()
        input_date = datetime.date(sender.input_date_year,
                                   sender.input_date_month,
                                   day)
        sender.input_line_data.append(input_date.isoformat())

        if sender.input_line_type == 'timetable_date':
            start_time = datetime.datetime.combine(input_date,
                                                   datetime.time.min)
            end_time = start_time + datetime.timedelta(days=1)
            cmd_result = booking_db.get_timetable(sender.user_id, start_time,
                                                  end_time)
            sender.start_input_line(None)
            msg_text = format_timetable(cmd_result)
        elif sender.input_line_type == 'book':
            msg_text = message_book_1
            markup = None
        booking_db.save_user_data(user_data_file)
    except BotCommandException as exception:
        exc = exception
        sender.start_input_line(None)
    except Exception:
        logger.error('Error ocurred when executing button timetable_date')
        raise
    bot.send_message(
        chat_id, get_error_message(exc, if_ok=msg_text),
        reply_markup=markup)
    bot.answer_callback_query(call.id, text='')


@bot.message_handler()
def process_text(message):
    """Process text input."""
    sender_id = process_message_sender(message)
    sender = booking_db.get_user(sender_id)
    if sender is None:
        return

    msg_text = None
    exc = None
    markup = get_cmd_keyboard()
    try:
        if sender.input_line_type != 'book':
            raise BotBadInput()
        if sender.input_line_type == 'book':
            data_num = len(sender.input_line_data)
            if data_num == 1:
                try:
                    input_time = booking.process_time(message.text)
                except ValueError:
                    raise BotBadInput()
                sender.input_line_data.append(input_time.isoformat())
                msg_text = message_book_2
                markup = None
            elif data_num == 2:
                try:
                    input_timedelta = booking.process_timedelta(message.text)
                except ValueError:
                    raise BotBadInput()
                sender.input_line_data.append(input_timedelta.total_seconds())
                msg_text = message_book_3
                markup = None
            elif data_num == 3:
                date = datetime.datetime.combine(
                    datetime.date.fromisoformat(sender.input_line_data[0]),
                    datetime.time.fromisoformat(sender.input_line_data[1]))
                duration = datetime.timedelta(
                    sender.input_line_data[2] // 86400,
                    sender.input_line_data[2] % 86400)
                booking_db.book(sender_id, date, duration, message.text)
            else:
                raise ValueError()
        booking_db.save_user_data(user_data_file)
    except BotCommandException as exception:
        exc = exception
        sender.start_input_line(None)
    except Exception:
        logger.error('Error ocurred when prcoessing text message')
        raise
    bot.send_message(message.chat.id, get_error_message(exc, if_ok=msg_text),
                     reply_markup=markup)


if __name__ == '__main__':
    logger.info('Started polling')
    bot.polling()
