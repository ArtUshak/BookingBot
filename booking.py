# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json
import logging

from exceptions import (BotCommandException, BotBadDateFormat, BotNoAccess,
                        BotBadInput, BotTimeOccupied, BotTimePassed,
                        BotBookingNotFound)

admins = []
whitelist = []
booking_data = None

minute_treshold = 15
TIME_AXIS = datetime(1970, 1, 1)


logger = logging.getLogger('bot')


def load_admins(filename):
    """
    Loads administrator list from file `filename`.
    """
    global admins
    logger.info('Loading admin list...')
    with open(filename, 'r', encoding='utf-8') as admins_file:
        for line in admins_file:
            data = line.strip()
            if len(data) == 0:
                continue
            if data[0] == '#':
                continue
            admins += [int(data)]


def load_whitelist(filename):
    """
    Loads whitelist from file `filename`, returns empty whitelist
    if an error occurred while reading file.
    """
    global whitelist
    logger.info('Loading whitelist...')
    try:
        with open(filename, 'r', encoding='utf-8') as whitelist_file:
            for line in whitelist_file:
                data = line.strip()
                if len(data) == 0:
                    continue
                if data[0] == '#':
                    continue
                whitelist += [int(data)]
    except FileNotFoundError:
        whitelist = []
    except BufferError:
        whitelist = []
    except EOFError:
        whitelist = []
    except ValueError:
        whitelist = []


def save_whitelist(filename):
    """
    Saves whitelist to file `filename`.
    """
    global whitelist
    with open(filename, 'w', encoding='utf-8') as whitelist_file:
        for whitelist_item in whitelist:
            whitelist_file.write(str(whitelist_item) + "\n")


def is_admin(user_id):
    """
    Returns `True` if user with ID `user_id` is administrator,
    otherwise `False`.
    """
    global admins
    if user_id < 0:
        return True
    return user_id in admins


def is_in_whitelist(user_id):
    """
    Returns `True` if user with ID `user_id` is in whitelist,
    otherwise `False`.
    """
    if is_admin(user_id):
        return True
    global whitelist
    return user_id in whitelist


def load_data_from_file(filename):
    """
    Tries to load booking data from file `filename`,
    returns None on any error.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as data_file:
            return json.load(data_file)
    except Exception:  # TODO
        return None


def init_data():
    """
    Initializes new empty booking data and returns it.
    """
    booking_data = []
    return booking_data


def load_data(filename):
    """
    Loads booking data from file `filename` and returns it,
    or initializes new data and returns it if an error occurred
    while loading data from file.
    """
    global booking_data
    booking_data = load_data_from_file(filename)
    if booking_data is None:
        booking_data = init_data()


def save_data(filename):
    """
    Saves booking data to file `filename`.
    """
    global booking_data
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])
    with open(filename, 'w', encoding='utf-8') as data_file:
        json.dump(booking_data, data_file)


def save_all_data(user_id, data_filename, whitelist_filename):
    """
    Command function.
    Saves booking data to file `data_filename` and whitelist to file
    `whitelist_filename`.
    If user with ID `user_id` do not have permissions to request
    this action, it will not be performed and `BotNoAccess` will be
    raised.
    """
    if not is_admin(user_id):
        raise BotNoAccess()
    save_data(data_filename)
    save_whitelist(whitelist_filename)


def is_free_time(time_data, duration):
    """
    Checks whether time starting from `time_data` with duration
    `duration` is free (not intersecting with any other booking
    items).
    If it is free, `True` is returned, otherwise `False`.
    Important notice: is start time of some item is equal to
    end time of another item, this is not considered intersection.
    """
    # TODO: probably optimize this code
    global booking_data
    for booking_data_item in booking_data:
        if booking_data_item[0] == time_data:
            return False
        if ((booking_data_item[0] < (time_data + duration))
                and ((booking_data_item[0] + booking_data_item[1])
                     > time_data)):
            return False
    return True


def book(user_id, time_data, duration, description):
    """
    Creates booking item for user with ID `user_id`, with time
    `time_data`, duration `duration` and description `description`.
    If user do not have permissions to request this action, it will
    not be performed and `BotNoAccess` will be raised.
    If time span is already occupied (is intersecting with some other
    item), action will not be performed and `BotTimeOccupied` will be
    raised.
    If time has already passed, action will not be performed and
    `BotTimePassed` will be raised.
    """
    global booking_data
    if not is_in_whitelist(user_id):
        raise BotNoAccess()
    if not is_free_time(time_data, duration):
        raise BotTimeOccupied()
    if time_data <= (datetime.now() - TIME_AXIS).total_seconds():
        raise BotTimePassed()
    booking_data.append([time_data, duration, description, user_id])
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])


def get_booking(time_data):
    """
    Returns array index of booking item which intersects with time
    `time_data`.
    If such item is not found, `-1` is returned.
    """
    global booking_data
    for i in range(len(booking_data)):
        booking_data_item = booking_data[i]

        if booking_data_item[0] == time_data:
            return i
        if ((booking_data_item[0] < (time_data))
                and ((booking_data_item[0] + booking_data_item[1])
                     > time_data)):
            return i
    return -1


def unbook(user_id, time_data, force=False):
    """
    Removes booking which intersects with time `time_data`.
    If the parameter `force` is set to `True`, removing of past
    bookings or other user's bookings is allowed (if user have right
    permissions).
    If user with ID `user_id` do not have permissions to request this
    action, it will not be performed and `BotNoAccess` will be raised.
    If time has already passed and `force` parameter is set to
    `False`, action will not be performed and `BotTimePassed` will be
    raised.
    If such booking is not found, action will not be performed and
    `BotBookingNotFound` will be raised.
    """
    global booking_data
    if not is_in_whitelist(user_id):
        raise BotNoAccess()
    if force:
        if not is_admin(user_id):
            raise BotNoAccess()
    if not force:
        if time_data <= (datetime.now() - TIME_AXIS).total_seconds():
            raise BotTimePassed()
    booking_id = get_booking(time_data)
    if booking_id < 0:
        raise BotBookingNotFound
    if not force:
        if booking_data[booking_id][3] != user_id:
            raise BotNoAccess
    booking_data.pop(booking_id)
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])


def get_timetable(user_id, start_time_data=-1, end_time_data=-1):
    """
    Returns timetable, list of booking items starting from
    `start_time_data` (or from the beginning if `start_time_data` is
    less than 0) and ending on `end_time_data` (or not ending if
    `end_time_data` is less than 0).
    """
    global booking_data
    result = []
    for booking_data_item in booking_data:
        if start_time_data >= 0:
            if (booking_data_item[0] + booking_data_item[1]) < start_time_data:
                continue
        if end_time_data >= 0:
            if booking_data_item[0] > end_time_data:
                continue
        result += [booking_data_item]
    return result


def process_date_time(date_str, time_str):
    """
    Parses date and time data from given date string `date_str`
    and time string `time_str` and returns number of seconds
    between that moment and `TIME_AXIS` (the 1970-01-01 00:00).
    """
    global minute_treshold
    try:
        data_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            data_date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            try:
                data_date = datetime.strptime(date_str, "%m-%d")
            except ValueError:
                data_date = datetime.strptime(date_str, "%d.%m")
    try:
        data_time = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        data_time = datetime.strptime(time_str, "%H:%M:%S")

    result = datetime.combine(data_date.date(), data_time.time())
    if result.year == 1900:
        result = datetime(
            datetime.today().year, result.month, result.day, result.hour,
            (result.minute // minute_treshold) * minute_treshold)
    else:
        result = datetime(
            result.year, result.month, result.day, result.hour,
            (result.minute // minute_treshold) * minute_treshold)
    return int((result - TIME_AXIS).total_seconds())


def process_time(time_str):
    """
    Parses time duration from given time string `time_str` and
    returns it as number of seconds.
    """
    if len(time_str.split(":")) == 1:
        data_timedelta = timedelta(
            minutes=((int(time_str) // minute_treshold) * minute_treshold))
    else:
        time_str_tokens = time_str.split(":")
        data_timedelta = timedelta(
            hours=((int(time_str_tokens[0]) // minute_treshold)
                   * minute_treshold),
            minutes=((int(time_str_tokens[1]) // minute_treshold)
                     * minute_treshold))

    return int(data_timedelta.total_seconds())
