#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram bot for booking auditorium (see `README.md`)."""
import calendar
import datetime
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import telebot
import telebot.types

import booking
import models
from botsettings import (calendar_locale, cmd_text_contactlist, cmd_text_help,
                         cmd_text_timetable, cmd_text_timetable_book,
                         cmd_text_timetable_date, cmd_text_timetable_today,
                         cmd_text_timetable_unbook, contactlist_file,
                         database_url, help_file, message_bad_date_format,
                         message_bad_input, message_book_1, message_book_2,
                         message_book_3, message_booking_not_found,
                         message_date_empty, message_input_date,
                         message_misc_error, message_no_access,
                         message_operation_ok, message_prompt_date,
                         message_time_occupied, message_time_passed,
                         message_timetable_date_row, message_timetable_header,
                         message_timetable_row, message_unbook_1,
                         message_username_not_found, message_whitelist_header,
                         message_whitelist_row, proxy_data, thread_number,
                         token)
from exceptions import (BotBadDateFormat, BotBadInput, BotBookingNotFound,
                        BotCommandException, BotDateEmpty, BotNoAccess,
                        BotTimeOccupied, BotTimePassed, BotUsernameNotFound)

logger = logging.getLogger('bot')


def get_help(help_filename: str) -> str:
    """
    Load help text.

    Load content of help text file `help_filename` and return it.
    """
    logger.info('Loading help text...')
    with open(help_filename, encoding='utf-8') as help_file:
        return help_file.read()


def get_contactlist(contactlist_filename: str) -> str:
    """
    Load contact list text.

    Load content of contact list text file `help_filename` and
    return it.
    """
    logger.info('Loading contact list...')
    with open(contactlist_filename, encoding='utf-8') \
            as contactlist_file:
        return contactlist_file.read()


logger.info('Starting bot...')

message_help: str = get_help(help_file)
logger.info('Help message:\n' + message_help)

message_contact_list: str = get_contactlist(contactlist_file)
logger.info('Contact list:\n' + message_contact_list)

models.db_init(database_url)

logger.info('Token loaded')

logger.info('Proxy data loaded')
if proxy_data is not None:
    telebot.apihelper.proxy = {
        proxy_data[0]: proxy_data[1]
    }

bot: telebot.TeleBot = telebot.TeleBot(token, num_threads=thread_number)

logger.info('Bot instance created')


def get_error_message(exception, if_ok: Optional[str] = None) -> str:
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
    elif isinstance(exception, BotDateEmpty):
        return message_date_empty
    else:
        return message_misc_error


def format_timetable(timetable_data: List[models.BookingItem]) -> str:
    """
    Return formatted timetable `timetable_data` as string.

    Timetable is given as a list of booking items.

    In resulting string each booking item should be placed on
    different line, with data about start and end time and
    description.
    """
    date: Optional[datetime.date] = None
    result: str = message_timetable_header + '\n'
    for timetable_item in timetable_data:
        if timetable_item.start_datetime.date() != date:
            date = timetable_item.start_datetime.date()
            date_str: str = timetable_item.start_datetime.strftime('%Y-%m-%d')
            result += message_timetable_date_row.format(date_str)
            result += '\n'
        result += message_timetable_row.format(
            timetable_item.start_datetime.strftime('%H:%M'),
            timetable_item.end_datetime.strftime('%H:%M'),
            timetable_item.description
        )
        result += '\n'
    return result


def split_message(message: str, max_length: int) -> List[str]:
    """
    Split message string to list if necessary.

    Split message string to list of strings with length less
    than `max_length`.
    """
    result: List[str] = []
    while len(message) > max_length:
        split_position: int = message.rfind('\n', 1, max_length)
        if split_position < 0:
            split_position = message.rfind(' ', 1, max_length)
        if split_position < 0:
            split_position = max_length
        result.append(message[:split_position])
        message = message[split_position + 1:]
    if len(message) > 0:
        result.append(message)
    return result


def send_message(
    chat_id: int, message_text: str,
    reply_markup: telebot.types.InlineKeyboardMarkup = None
) -> None:
    """Process message and send it to chat with id `chat_id`."""
    message_parts: List[str] = split_message(message_text, 4096)
    if len(message_parts) == 0:
        return
    for message_part in message_parts[:-1]:
        bot.send_message(chat_id, message_part)
    bot.send_message(chat_id, message_parts[-1], reply_markup=reply_markup)


def bot_command_handler(
    name: str, param_num_min: int = -1, param_maxsplit: int = -1,
    need_transaction: bool = True
) -> Callable[
        [Callable[[telebot.types.Message, models.User,
                   List[str]], Optional[Dict[str, Any]]]],
        Callable[[telebot.types.Message], None],
]:
    """
    Create decorator for command hanling.

    This decorator will wrap handler functions with code that can take
    care of getting sender ID, sending error messages, etc.
    """
    def wrapper(
        func: Callable[[telebot.types.Message, models.User,
                        List[str]], Optional[Dict[str, Any]]]
    ) -> Callable[[telebot.types.Message], None]:
        def wrapper_func(message: telebot.types.Message) -> None:
            with models.db_proxy:
                sender: models.User = process_message_sender(message)
                logger.info(
                    'Called command {} from user {} ({})'.format(
                        name, sender.user_id, message.from_user.username
                    )
                )
                exc: Optional[Exception] = None
                result: Optional[Dict[str, Any]] = None  # TODO: typing
                try:
                    message_tokens: List[str] = message.text.split(
                        maxsplit=param_maxsplit)
                    if len(message_tokens) < param_num_min:
                        raise BotBadInput()

                    result = func(message, sender, message_tokens)

                except BotCommandException as exception:
                    exc = exception
                except Exception:
                    logger.error(
                        'Error occurred when executing command {}'.format(
                            name
                        )
                    )
                    raise

                result_message: Optional[Any] = None
                result_markup: Optional[Any] = None
                if result is not None:
                    result_message = result.get('message')
                    result_markup = result.get('markup')
                try:
                    send_message(
                        message.chat.id,
                        get_error_message(exc, if_ok=result_message),
                        reply_markup=result_markup
                    )
                except telebot.apihelper.ApiException as api_exc:
                    if api_exc.result.status_code not in [403]:
                        raise

        return wrapper_func

    return wrapper


def bot_button_handler(
    name: str, need_transaction: bool = True
) -> Callable[
    [Callable[[telebot.types.CallbackQuery, models.User],
              Optional[Dict[str, Any]]]],
    Callable[[telebot.types.CallbackQuery], None]
]:
    """
    Create decorator for button hanling.

    This decorator will wrap handler functions with code that can take
    care of getting sender ID, sending error messages, etc.
    """
    def wrapper(
        func: Callable[[telebot.types.CallbackQuery,
                        models.User], Optional[Dict[str, Any]]]
    ) -> Callable[[telebot.types.CallbackQuery], None]:
        def wrapper_func(call: telebot.types.CallbackQuery) -> None:
            with models.db_proxy:
                chat_id: int = call.message.chat.id
                sender: Optional[models.User] = booking.get_user_by_chat_id(
                    chat_id)
                if sender is None:
                    return
                logger.info('Called button {} from user {}'.format(
                    name, sender.user_id))
                exc: Optional[Exception] = None
                result: Optional[Dict[str, Any]] = None  # TODO: typing
                result_ignore: Optional[Any] = None
                result_message: Optional[Any] = None
                result_markup: Optional[Any] = None
                result_edit_markup: Optional[Any] = None
                result_edit_message: Optional[Any] = None
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
                        try:
                            bot.edit_message_text(
                                get_error_message(
                                    exc, if_ok=result_edit_message
                                ),
                                call.from_user.id, call.message.message_id,
                                reply_markup=result_edit_markup
                            )
                        except telebot.apihelper.ApiException as api_exc:
                            if api_exc.result.status_code not in [403]:
                                raise
                    else:
                        try:
                            bot.edit_message_reply_markup(
                                call.from_user.id, call.message.message_id,
                                reply_markup=None
                            )
                            send_message(
                                chat_id,
                                get_error_message(exc, if_ok=result_message),
                                reply_markup=result_markup
                            )
                        except telebot.apihelper.ApiException as api_exc:
                            if api_exc.result.status_code not in [403]:
                                raise
                bot.answer_callback_query(call.id, text='')

        return wrapper_func

    return wrapper


def format_whitelist(whitelist: List[Tuple[int, str]]) -> str:
    """
    Return formatted whitelist `whitelist` as string.

    Whitelist is given as a list of tuples of user IDs and usernames.

    In resulting string each user should be placed on
    different line.
    """
    result: str = message_whitelist_header + '\n'
    for whitelist_item in whitelist:
        result += message_whitelist_row.format(*whitelist_item)
        result += '\n'
    return result


def process_message_sender(
    message: telebot.types.Message
) -> models.User:
    """
    Process message and update user data.

    Process `message`, update user data and return user id from `message`.
    """
    chat_id: int = message.chat.id
    user_id: int = message.from_user.id
    username: str = message.from_user.username
    user: models.User = booking.update_user_data(user_id, chat_id, username)
    return user


@bot.callback_query_handler(func=lambda call: call.data == 'help')
@bot_button_handler('help')
def process_button_help(
    _call: telebot.types.CallbackQuery, _sender: models.User
) -> Optional[Dict[str, Any]]:
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
def process_cmd_help(
    message: telebot.types.Message, _sender: models.User, _params: List[str]
) -> Optional[Dict[str, Any]]:
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
def get_calendar_keyboard(
    year: int, month: int
) -> telebot.types.InlineKeyboardMarkup:
    """
    Create inline keyboard for calendar and return it.

    Calendar will be created for `year` and `month`.
    """
    # TODO: refactor
    markup = telebot.types.InlineKeyboardMarkup()
    text_calendar = calendar.LocaleTextCalendar(locale=calendar_locale)

    # First row - month and year
    row: List[telebot.types.InlineKeyboardButton] = []
    row.append(
        telebot.types.InlineKeyboardButton(
            text_calendar.formatmonthname(year, month, 100).strip(),
            callback_data='ignore'
        )
    )
    markup.row(*row)

    # Second row - week days
    week_days: List[str] = [
        text_calendar.formatweekday(i, 8).strip() for i in range(7)
    ]
    row = []
    for week_day in week_days:
        row.append(telebot.types.InlineKeyboardButton(
            week_day, callback_data='ignore'
        ))
    markup.row(*row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(telebot.types.InlineKeyboardButton(
                    ' ', callback_data='ignore'
                ))
            else:
                row.append(telebot.types.InlineKeyboardButton(
                    str(day), callback_data='calendar_day:{}'.format(day)
                ))
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


def get_date_booking_selection_keyboard(
    date: datetime.date
) -> telebot.types.InlineKeyboardMarkup:
    """
    Create inline keyboard to select booking item in date and return it.

    If there are no items for that day, return `None`.
    """
    keyboard: telebot.types.InlineKeyboardMarkup = \
        telebot.types.InlineKeyboardMarkup()
    booking_items = models.BookingItem.select().where(
        (models.BookingItem.start_datetime < (date + datetime.timedelta(1)))
        & (models.BookingItem.end_datetime >= date)
    )
    if not booking_items:
        return None
    for booking_item in booking_items:
        keyboard.add(telebot.types.InlineKeyboardButton(
            text='{}-{} {}'.format(
                booking_item.start_datetime, booking_item.end_datetime,
                booking_item.description
            ),
            callback_data='booking_item:{}'.format(booking_item.get_id())
        ))
    return keyboard


def get_cmd_keyboard() -> telebot.types.InlineKeyboardMarkup:
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
def process_button_book(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `book`.

    Start input to add new booking item.
    """
    if not sender.get_is_in_whitelist():
        raise BotNoAccess()
    sender.start_input_line_book()
    return {
        'message': message_prompt_date,
        'markup': get_calendar_keyboard(sender.input_calendar.year,
                                        sender.input_calendar.month),
    }


@bot.message_handler(commands=['book'])
@bot_command_handler('/book', param_num_min=5, param_maxsplit=4)
def process_cmd_book(
    message: telebot.types.Message, sender: models.User,
    params: List[str]
) -> Optional[Dict[str, Any]]:
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
        booking.book(sender, time, duration, description)
    return None


@bot.callback_query_handler(func=lambda call: call.data == 'unbook')
@bot_button_handler('unbook')
def process_button_unbook(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `unbook`.

    Start inputting data to remove booking.
    """
    if not sender.get_is_in_whitelist():
        raise BotNoAccess()
    sender.start_input_line_unbook()
    return {
        'message': message_prompt_date,
        'markup': get_calendar_keyboard(sender.input_calendar.year,
                                        sender.input_calendar.month),
    }


def execute_cmd_unbook(
    message: telebot.types.Message, sender: models.User,
    params: List[str], force: bool
) -> Optional[Dict[str, Any]]:
    """Execute unbook command with given `force` parameter."""
    date_str = params[1]
    time_str = params[2]
    logger.info(
        'Called /unbook for date {}, time {}'.format(date_str, time_str))
    try:
        time = booking.process_date_time(date_str, time_str)
    except ValueError:
        raise BotBadInput()
    else:
        booking.unbook(sender, time, force=force)
    return None


@bot.message_handler(commands=['unbook'])
@bot_command_handler('/unbook', param_num_min=3, param_maxsplit=3)
def process_cmd_unbook(
    message: telebot.types.Message, sender: models.User,
    params: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Command `/unbook`.

    Syntax: `/unbook <DATE> <TIME>`

    Remove booking that intersect with moment `<DATE> <TIME>`. Do not
    remove booking if it was not added by current user or if it has
    already passed.
    """
    return execute_cmd_unbook(message, sender, params, False)


@bot.message_handler(commands=['unbook_force'])
@bot_command_handler('/unbook_force', param_num_min=3, param_maxsplit=3)
def process_cmd_unbook_force(
    message: telebot.types.Message, sender: models.User,
    params: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Command `/unbook_force`.

    Syntax: `/unbook_force <DATE> <TIME>`

    Remove booking that intersect with moment `<DATE> <TIME>` without
    restrictions applied `/unbook` command, although still respecting
    user permissions.
    """
    return execute_cmd_unbook(message, sender, params, True)


@bot.callback_query_handler(func=lambda call: call.data == 'timetable')
@bot_button_handler('timetable')
def process_button_timetable(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
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
def process_button_timetable_today(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `timetable_today`.

    Display timetable for current day.
    """
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
def process_button_timetable_date(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `timetable_date`.

    Start inputting data to display timetable for given day.
    """
    sender.start_input_line_timetable_date()
    return {
        'message': message_prompt_date,
        'markup': get_calendar_keyboard(sender.input_calendar.year,
                                        sender.input_calendar.month),
    }


@bot.message_handler(commands=['timetable'])
@bot_command_handler('/timetable', param_maxsplit=2)
def process_cmd_timetable(
    message: telebot.types.Message, sender: models.User,
    params: List[str]
) -> Optional[Dict[str, Any]]:
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

    timetable = booking.get_timetable(sender, start_time, end_time)
    return {
        'message': format_timetable(timetable),
    }


@bot.message_handler(commands=['logmyinfo'])
@bot_command_handler('/logmyinfo')
def process_cmd_logmyinfo(
    message: telebot.types.Message, _sender: models.User, _params: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Command `/logmyinfo`.

    Syntax: `/logmyinfo`

    Do nothing, just write user ID and username to log and remember user data.
    """
    return None


@bot.callback_query_handler(func=lambda call: call.data == 'contactlist')
@bot_button_handler('contactlist')
def process_button_contactlist(
    _call: telebot.types.CallbackQuery, _sender: models.User
) -> Optional[Dict[str, Any]]:
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
def process_cmd_contactlist(
    message: telebot.types.Message, _sender: models.User, _params: List[str]
) -> Optional[Dict[str, Any]]:
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
def process_cmd_whitelist(
    message: telebot.types.Message, sender: models.User, params: List[str]
) -> Optional[Dict[str, Any]]:
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
        whitelist = booking.get_whitelist(sender)
        msg_text = format_whitelist(whitelist)
    elif len(params) == 3:
        action_str = params[1].lower()
        username = params[2]
        if action_str == 'add':
            booking.add_user_to_whitelist(sender, username)
        elif action_str == 'remove':
            booking.remove_user_from_whitelist(sender, username)
        else:
            raise BotBadInput()
    else:
        raise BotBadInput()
    return {
        'message': msg_text
    }


@bot.callback_query_handler(func=lambda call: call.data == 'next_month')
@bot_button_handler('next_month')
def process_button_next_month(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `next_month`.

    Change to next month if calendar is shown.
    """
    if not sender.input_calendar:
        return None

    sender.input_calendar.next_month()
    return {
        'edit_message': message_prompt_date,
        'edit_markup': get_calendar_keyboard(sender.input_calendar.year,
                                             sender.input_calendar.month),
    }


@bot.callback_query_handler(func=lambda call: call.data == 'previous_month')
@bot_button_handler('previous_month')
def process_button_previous_month(
    _call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `previous_month`.

    Change to previous month if calendar is shown.
    """
    if not sender.input_calendar:
        return None

    if sender.input_calendar.previous_month():
        return {
            'edit_message': message_prompt_date,
            'edit_markup': get_calendar_keyboard(sender.input_calendar.year,
                                                 sender.input_calendar.month),
        }
    else:
        return {
            'ignore': True,
        }


@bot.callback_query_handler(func=lambda call: call.data == 'ignore')
def process_button_ignore(call: telebot.types.CallbackQuery) -> None:
    """
    Button `ignore`.

    Ignore button input, only mark it as answered.
    """
    bot.answer_callback_query(call.id, text='')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('calendar_day:'))
@bot_button_handler('calendar_day')
def process_button_calendar_day(
    call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `calendar_day:<DAY>`.

    Process calendar input of day `<DAY>`.
    """
    if not sender.input_calendar:
        return None

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
        send_message(
            call.message.chat.id,
            message_input_date.format(input_date)
        )
    except telebot.apihelper.ApiException as api_exc:
        if api_exc.result.status_code not in [403]:
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
        next_day_start = (
            datetime.datetime.combine(input_date, datetime.time())
            + datetime.timedelta(days=1)
        )
        if next_day_start < datetime.datetime.now():
            raise BotTimePassed()
        sender.input_line_book.start_date = input_date
        sender.input_line_book.save()
        return {
            'message': message_book_1,
            'markup': None,
        }
    elif sender.input_line_type == 'UNBOOK':
        sender.input_line_unbook.start_date = input_date
        markup = get_date_booking_selection_keyboard(
            input_date
        )
        if markup is None:
            raise BotDateEmpty()
        sender.input_line_unbook.start_date = input_date
        sender.input_line_unbook.save()
        return {
            'message': message_unbook_1,
            'markup': markup,
        }

    return None


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('booking_item:'))
@bot_button_handler('booking_item')
def process_button_booking_item(
    call: telebot.types.CallbackQuery, sender: models.User
) -> Optional[Dict[str, Any]]:
    """
    Button `booking_item:<ID>`.

    Process calendar input of selecting booking item `<ID>`.
    """
    if not sender.input_calendar:
        return None

    regex_match = re.match(r'booking_item:([0-9]+)', call.data)

    if regex_match is None:
        raise BotBadInput()
    booking_item_id = int(regex_match.group(1))
    booking_item = models.BookingItem.get_by_id(booking_item_id)

    if sender.input_line_type == 'UNBOOK':
        booking.unbook_item(sender, booking_item)
        sender.clear_input_line()

    return {
        'message': message_operation_ok,
        'markup': get_cmd_keyboard(),
    }


@bot.message_handler()
def process_text(message: telebot.types.Message) -> None:
    """Process text input."""
    sender = process_message_sender(message)
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
                raise BotBadInput()
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
                booking.book(sender, date, duration, message.text)
                sender.clear_input_line()
        elif sender.input_line_type == 'UNBOOK':
            try:
                input_time = booking.process_time(message.text)
            except ValueError:
                raise BotBadInput()
            if sender.input_line_unbook.start_date is None:
                raise BotBadInput()
            else:
                date = datetime.datetime.combine(
                    sender.input_line_unbook.start_date,
                    input_time)
                booking.unbook(sender, date)
                sender.clear_input_line()

    except BotCommandException as exception:
        exc = exception
        sender.clear_input_line()
    except Exception:
        logger.error('Error occurred when processing text message')
        raise
    try:
        send_message(
            message.chat.id,
            get_error_message(exc, if_ok=msg_text),
            reply_markup=markup
        )
    except telebot.apihelper.ApiException as api_exc:
        if api_exc.result.status_code not in [403]:
            raise


if __name__ == '__main__':
    logger.info('Started polling')
    bot.polling()
