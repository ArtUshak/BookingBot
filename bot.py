# -*- coding: utf-8 -*-
"""Telegram bot for booking auditorium (see `README.md`)."""
import calendar
import datetime
import logging
import re

import telebot
import telebot.types

import booking
import models
from botsettings import (message_indev, message_operation_ok,
                         message_bad_input, message_bad_date_format,
                         message_no_access, message_misc_error,
                         message_time_occupied, message_time_passed,
                         message_booking_not_found, message_username_not_found,
                         message_timetable_header, message_timetable_date_row,
                         message_timetable_row, message_whitelist_header,
                         message_whitelist_row, message_input_date,
                         cmd_text_timetable, cmd_text_timetable_today,
                         cmd_text_timetable_date,
                         cmd_text_timetable_book, cmd_text_timetable_unbook,
                         cmd_text_contactlist, cmd_text_help,
                         message_prompt_date,
                         message_book_1, message_book_2, message_book_3,
                         message_unbook_1,
                         contactlist_file, help_file, token_file, proxy_file,
                         database_file)
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

    Load proxy type and URL from from first line of file `filename`
    and return it as tuple of strings, without leading and trailing
    whitespaces.
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

models.db_init(database_file)

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
        curr_date_str = timetable_item.start_datetime.strftime('%Y-%m-%d')
        if date_str != curr_date_str:
            date_str = curr_date_str
            result += message_timetable_date_row.format(date_str)
            result += '\n'
        result += message_timetable_row.format(
            timetable_item.start_datetime.strftime('%H:%M'),
            timetable_item.end_datetime.strftime('%H:%M'),
            timetable_item.description
        )
        result += '\n'
    return result


def bot_command_handler(name, param_num_min=-1, param_maxsplit=-1,
                        need_transaction=True):
    """
    Create decorator for command hanling.

    This decorator will wrap handler functions with code that can take
    care of getting sender ID, sending error messages, etc.
    """
    def wrapper(func):
        def wrapper_func(message):
            with models.db_proxy:
                sender_id = process_message_sender(message)
                logger.info(
                    'Called command {} from user {} ({})'.format(
                        name, sender_id, message.from_user.username
                    )
                )
                exc = None
                result = None
                try:
                    message_tokens = message.text.split(
                        maxsplit=param_maxsplit)
                    if len(message_tokens) < param_num_min:
                        raise BotBadInput()

                    result = func(message, sender_id, message_tokens)

                except BotCommandException as exception:
                    exc = exception
                except Exception:
                    logger.error(
                        'Error occurred when executing command {}'.format(
                            name
                        )
                    )
                    raise

                result_message = None
                result_markup = None
                if result is not None:
                    result_message = result.get('message')
                    result_markup = result.get('markup')
                try:
                    bot.send_message(message.chat.id,
                                     get_error_message(
                                         exc, if_ok=result_message),
                                     reply_markup=result_markup)
                except telebot.apihelper.ApiException as exc:
                    if exc.result.status_code not in [403]:
                        raise

        return wrapper_func

    return wrapper


def bot_button_handler(name, need_transaction=True):
    """
    Create decorator for button hanling.

    This decorator will wrap handler functions with code that can take
    care of getting sender ID, sending error messages, etc.
    """
    def wrapper(func):
        def wrapper_func(call):
            with models.db_proxy:
                chat_id = call.message.chat.id
                sender = booking.get_user_by_chat_id(chat_id)
                if sender is None:
                    return
                logger.info('Called button {} from user {}'.format(
                    name, sender.user_id))
                exc = None
                result = None
                result_ignore = None
                result_message = None
                result_markup = None
                result_edit_markup = None
                result_edit_message = None
                try:
                    result = func(call, sender)
                except BotCommandException as exception:
                    exc = exception
                    result_markup = get_cmd_keyboard()
                    sender.clear_input_line()
                except Exception:
                    logger.error(
                        'Error occurred when executing button {}'.format(
                            name
                        )
                    )
                    raise

                if result is not None:
                    result_message = result.get('message')
                    result_markup = result.get('markup')
                    result_edit_markup = result.get('edit_markup')
                    result_edit_message = result.get('edit_message')
                    result_ignore = result.get('ignore')
                if not result_ignore:
                    if ((result_edit_markup is not None)
                            or (result_edit_message is not None)):
                        bot.edit_message_text(
                            get_error_message(exc, if_ok=result_edit_message),
                            call.from_user.id, call.message.message_id,
                            reply_markup=result_edit_markup)
                    else:
                        try:
                            bot.send_message(
                                chat_id, get_error_message(
                                    exc, if_ok=result_message),
                                reply_markup=result_markup)
                        except telebot.apihelper.ApiException as exc:
                            if exc.result.status_code not in [403]:
                                raise
                bot.answer_callback_query(call.id, text='')

        return wrapper_func

    return wrapper


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
    booking.update_user_data(user_id, chat_id, username)
    return user_id


@bot.callback_query_handler(func=lambda call: call.data == 'help')
@bot_button_handler('help')
def process_button_help(_call, _sender):
    """
    Button `help`.

    Display help text message.
    """
    return {
        'message': message_help,
        'markup': get_cmd_keyboard(),
    }


@bot.message_handler(commands=['start', 'help'])
@bot_command_handler('/help')
def process_cmd_help(message, _sender_id, _params):
    """
    Command `/help`.

    Syntax: `/help`

    Syntax: `/start`

    Display help text message.
    """
    return {
        'message': message_help,
        'markup': get_cmd_keyboard(),
    }


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
@bot_button_handler('book')
def process_button_book(_call, sender):
    """
    Button `book`.

    Start input to add new booking item.
    """
    if not sender.get_is_in_whitelist():
        raise BotNoAccess()
    sender.start_input_line_book()
    return {
        'message': message_prompt_date,
        'markup': get_calendar(sender.input_calendar.year,
                               sender.input_calendar.month),
    }


@bot.message_handler(commands=['book'])
@bot_command_handler('/book', param_num_min=5, param_maxsplit=4)
def process_cmd_book(message, sender_id, params):
    """
    Command `/book`.

    Syntax: `/book <DATE> <TIME> <DURATION> <DESCRIPTION>`

    Add new booking item starting from moment `<DATE> <TIME>` and
    ending at moment `<DATE> <TIME> + <DURATION>` with description
    `<DESCRIPTION>`.
    """
    date_str = params[1]
    time_str = params[2]
    duration_str = params[3]
    description = params[4]
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
        booking.book(sender_id, time, duration, description)


@bot.callback_query_handler(func=lambda call: call.data == 'unbook')
@bot_button_handler('unbook')
def process_button_unbook(_call, sender):
    """
    Button `unbook`.

    Start inputting data to remove booking.
    """
    if not sender.get_is_in_whitelist():
        raise BotNoAccess()
    sender.start_input_line_unbook()
    return {
        'message': message_prompt_date,
        'markup': get_calendar(sender.input_calendar.year,
                               sender.input_calendar.month),
    }


@bot.message_handler(commands=['unbook'])
@bot_command_handler('/unbook', param_num_min=3, param_maxsplit=3)
def process_cmd_unbook(message, sender_id, params):
    """
    Command `/unbook`.

    Syntax: `/unbook <DATE> <TIME>`

    Remove booking that intersect with moment `<DATE> <TIME>`. Do not
    remove booking if it was not added by current user or if it has
    already passed.
    """
    date_str = params[1]
    time_str = params[2]
    logger.info(
        'Called /unbook for date {}, time {}'.format(date_str, time_str))
    try:
        time = booking.process_date_time(date_str, time_str)
    except ValueError:
        raise BotBadInput()
    else:
        booking.unbook(sender_id, time)


@bot.message_handler(commands=['unbook_force'])
@bot_command_handler('/unbook_force', param_num_min=3, param_maxsplit=3)
def process_cmd_unbook_force(message, sender_id, params):
    """
    Command `/unbook_force`.

    Syntax: `/unbook_force <DATE> <TIME>`

    Remove booking that intersect with moment `<DATE> <TIME>` without
    restrictions applied `/unbook` command, although still respecting
    user permissions.
    """
    date_str = params[1]
    time_str = params[2]
    logger.info(
        'Called /unbook for date {}, time {}'.format(date_str, time_str))
    try:
        time = booking.process_date_time(date_str, time_str)
    except ValueError:
        raise BotBadInput()
    else:
        booking.unbook(sender_id, time, force=True)


@bot.callback_query_handler(func=lambda call: call.data == 'timetable')
@bot_button_handler('timetable')
def process_button_timetable(_call, sender):
    """
    Button `timetable`.

    Display timetable for all timeline since current day.
    """
    start_time = datetime.datetime.today()
    end_time = None
    timetable = booking.get_timetable(sender.user_id, start_time,
                                      end_time)
    return {
        'message': format_timetable(timetable),
        'markup': get_cmd_keyboard(),
    }


@bot.callback_query_handler(func=lambda call: call.data == 'timetable_today')
@bot_button_handler('timetable_today')
def process_button_timetable_today(_call, sender):
    """
    Button `timetable_today`.

    Display timetable for current day.
    """
    timetable = []
    start_time = datetime.datetime.today()
    end_time = start_time + datetime.timedelta(days=1)
    timetable = booking.get_timetable(sender.user_id, start_time,
                                      end_time)
    return {
        'message': format_timetable(timetable),
        'markup': get_cmd_keyboard(),
    }


@bot.callback_query_handler(func=lambda call: call.data == 'timetable_date')
@bot_button_handler('timetable_date')
def process_button_timetable_date(_call, sender):
    """
    Button `timetable_date`.

    Start inputting data to display timetable for given day.
    """
    sender.start_input_line_timetable_date()
    return {
        'message': message_prompt_date,
        'markup': get_calendar(sender.input_calendar.year,
                               sender.input_calendar.month),
    }


@bot.message_handler(commands=['timetable'])
@bot_command_handler('/timetable', param_maxsplit=2)
def process_cmd_timetable(message, sender_id, params):
    """
    Command `/timetable`.

    Syntax: `/timetable`

    Syntax: `/timetable TODAY`

    Syntax: `/timetable <DATE>`

    Display timetable for all timeline since current day (if no
    parameters were given), for current day (if parameter was TODAY)
    or for `<DATE>` (if it was given).
    """
    start_time = datetime.datetime.today()
    end_time = None
    if len(params) >= 2:
        params = message.text.split(' ', 2)
        if params[1].lower() == 'today':
            end_time = (datetime.datetime.today()
                        + datetime.timedelta(days=1))
        else:
            try:
                start_date = booking.process_date(params[1])
            except ValueError:
                raise BotBadDateFormat()
            start_time = datetime.datetime.combine(start_date,
                                                   datetime.time.min)
            end_time = start_time + datetime.timedelta(days=1)

    timetable = booking.get_timetable(sender_id, start_time, end_time)
    return {
        'message': format_timetable(timetable),
    }


@bot.message_handler(commands=['logmyinfo'])
@bot_command_handler('/logmyinfo')
def process_cmd_logmyinfo(message, _sender_id, _params):
    """
    Command `/logmyinfo`.

    Syntax: `/logmyinfo`

    Do nothing, just write user ID and username to log and remember user data.
    """
    pass


@bot.callback_query_handler(func=lambda call: call.data == 'contactlist')
@bot_button_handler('contactlist')
def process_button_contactlist(_call, _sender):
    """
    Button `contactlist`.

    Display contact list text message.
    """
    return {
        'message': message_contact_list,
        'markup': get_cmd_keyboard(),
    }


@bot.message_handler(commands=['contactlist'])
@bot_command_handler('/contactlist')
def process_cmd_contactlist(message, _sender_id, _params):
    """
    Command `/contactlist`.

    Syntax: `/contactlist`

    Display contact list text message.
    """
    return {
        'message': message_contact_list
    }


@bot.message_handler(commands=['whitelist'])
@bot_command_handler('/whitelist', param_maxsplit=3)
def process_cmd_whitelist(message, sender_id, params):
    """
    Command `/whitelist`.

    Syntax: `/whitelist`

    Syntax: `/whitelist ADD <USERNAME>`

    Syntax: `/whitelist REMOVE <USERNAME>`

    Display current whitelist (if no parameters were given) or
    add user `<USERNAME>` or remove him from whitelist.
    This command is administrator-only.
    """
    msg_text = None
    if len(params) == 1:
        whitelist = booking.get_whitelist(sender_id)
        msg_text = format_whitelist(whitelist)
    elif len(params) == 3:
        action_str = params[1].lower()
        username = params[2]
        if action_str == 'add':
            booking.add_user_to_whitelist(sender_id, username)
        elif action_str == 'remove':
            booking.remove_user_from_whitelist(sender_id, username)
        else:
            raise BotBadInput()
    else:
        raise BotBadInput()
    return {
        'message': msg_text
    }


@bot.callback_query_handler(func=lambda call: call.data == 'next_month')
@bot_button_handler('next_month')
def process_button_next_month(_call, sender):
    """
    Button `next_month`.

    Change to next month if calendar is shown.
    """
    if not sender.input_calendar:
        return

    sender.input_calendar.next_month()
    return {
        'edit_message': message_prompt_date,
        'edit_markup': get_calendar(sender.input_calendar.year,
                                    sender.input_calendar.month),
    }


@bot.callback_query_handler(func=lambda call: call.data == 'previous_month')
@bot_button_handler('previous_month')
def process_button_previous_month(_call, sender):
    """
    Button `previous_month`.

    Change to previous month if calendar is shown.
    """
    if not sender.input_calendar:
        return

    if sender.input_calendar.previous_month():
        return {
            'edit_message': message_prompt_date,
            'edit_markup': get_calendar(sender.input_calendar.year,
                                        sender.input_calendar.month),
        }
    else:
        return {
            'ignore': True,
        }


@bot.callback_query_handler(func=lambda call: call.data == 'ignore')
def process_button_ignore(call):
    """
    Button `ignore`.

    Ignore button input, only mark it as answered.
    """
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('calendar_day:'))
@bot_button_handler('calendar_day')
def process_button_calendar_day(call, sender):
    """
    Button `calendar_day:<DAY>`.

    Process calendar input of day `<DAY>`.
    """
    if not sender.input_calendar:
        return

    regex_match = re.match(r'calendar_day:([0-9]+)', call.data)
    if regex_match is None:
        raise BotBadInput()
    day = int(regex_match.group(1))

    if sender.input_line_type is None:
        raise BotBadInput()

    input_date = datetime.date(sender.input_calendar.year,
                               sender.input_calendar.month,
                               day)
    try:
        bot.send_message(call.message.chat.id,
                         message_input_date.format(input_date))
    except telebot.apihelper.ApiException as exc:
        if exc.result.status_code not in [403]:
            raise

    if sender.input_line_type == 'TIMETABLE_DATE':
        start_time = datetime.datetime.combine(input_date,
                                               datetime.time.min)
        end_time = start_time + datetime.timedelta(days=1)
        timetable = booking.get_timetable(sender.user_id, start_time,
                                          end_time)
        sender.clear_input_line()
        return {
            'message': format_timetable(timetable),
            'markup': get_cmd_keyboard(),
        }
    elif sender.input_line_type == 'BOOK':
        sender.input_line_book.start_date = input_date
        sender.input_line_book.save()
        return {
            'message': message_book_1,
            'markup': None,
        }
    elif sender.input_line_type == 'UNBOOK':
        sender.input_line_unbook.start_date = input_date
        sender.input_line_unbook.save()
        return {
            'message': message_unbook_1,
            'markup': None,
        }


@bot.message_handler()
def process_text(message):
    """Process text input."""
    sender_id = process_message_sender(message)
    sender = booking.get_user(sender_id)
    if sender is None:
        return

    msg_text = None
    exc = None
    markup = get_cmd_keyboard()
    try:
        if ((sender.input_line_type != 'BOOK')
                and (sender.input_line_type != 'UNBOOK')):
            raise BotBadInput()
        if sender.input_line_type == 'BOOK':
            if sender.input_line_book.start_date is None:
                raise ValueError()
            elif sender.input_line_book.start_time is None:
                try:
                    input_time = booking.process_time(message.text)
                except ValueError:
                    raise BotBadInput()
                sender.input_line_book.start_time = input_time
                sender.input_line_book.save()
                msg_text = message_book_2
                markup = None
            elif sender.input_line_book.duration_seconds is None:
                try:
                    input_timedelta = booking.process_timedelta(message.text)
                except ValueError:
                    raise BotBadInput()
                sender.input_line_book.duration_seconds = \
                    input_timedelta.total_seconds()
                sender.input_line_book.save()
                msg_text = message_book_3
                markup = None
            else:
                date = datetime.datetime.combine(
                    sender.input_line_book.start_date,
                    sender.input_line_book.start_time)
                duration = datetime.timedelta(
                    sender.input_line_book.duration_seconds // 86400,
                    sender.input_line_book.duration_seconds % 86400)
                booking.book(sender_id, date, duration, message.text)
                sender.clear_input_line()
        elif sender.input_line_type == 'UNBOOK':
            try:
                input_time = booking.process_time(message.text)
            except ValueError:
                raise BotBadInput()
            if sender.input_line_unbook.start_date is None:
                raise ValueError()
            else:
                date = datetime.datetime.combine(
                    sender.input_line_unbook.start_date,
                    input_time)
                booking.unbook(sender_id, date)
                sender.clear_input_line()

    except BotCommandException as exception:
        exc = exception
        sender.clear_input_line()
    except Exception:
        logger.error('Error occurred when processing text message')
        raise
    try:
        bot.send_message(message.chat.id,
                         get_error_message(exc, if_ok=msg_text),
                         reply_markup=markup)
    except telebot.apihelper.ApiException as exc:
        if exc.result.status_code not in [403]:
            raise


if __name__ == '__main__':
    logger.info('Started polling')
    bot.polling()
