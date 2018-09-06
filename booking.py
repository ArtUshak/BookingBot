# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json
import logging

from exceptions import (BotCommandException, BotBadDateFormat, BotNoAccess,
                        BotBadInput, BotTimeOccupied, BotTimePassed,
                        BotBookingNotFound)


logger = logging.getLogger('bot')

minute_treshold = 15
# TODO: use datetime module instead of seconds
TIME_AXIS = datetime(1970, 1, 1)


class BookingDB(object):
    def __init__(self, adminlist_filename, data_filename,
                 whitelist_filename):
        self.load_or_init_data(data_filename)
        if whitelist_filename is not None:
            self.load_whitelist(whitelist_filename)
        else:
            self.whitelist = []
        logger.info('Whitelist: {}'.format(str(self.whitelist)))
        if adminlist_filename is not None:
            self.load_admins(adminlist_filename)
        else:
            self.admins = []
        logger.info('Admins: {}'.format(str(self.admins)))

    def load_admins(self, filename):
        """
        Loads administrator list from file `filename`.
        """
        logger.info('Loading admin list...')
        self.admins = []
        with open(filename, 'r', encoding='utf-8') as admins_file:
            for line in admins_file:
                data = line.strip()
                if len(data) == 0:
                    continue
                if data[0] == '#':
                    continue
                self.admins.append(int(data))
        logger.info('Admin list loaded')

    def load_whitelist(self, filename):
        """
        Loads whitelist from file `filename`, returns empty whitelist
        if an error occurred while reading file.
        """
        logger.info('Loading whitelist...')
        self.whitelist = []
        try:
            with open(filename, 'r', encoding='utf-8') as whitelist_file:
                for line in whitelist_file:
                    data = line.strip()
                    if len(data) == 0:
                        continue
                    if data[0] == '#':
                        continue
                    self.whitelist.append(int(data))
        except FileNotFoundError:
            self.whitelist = []
        except BufferError:
            self.whitelist = []
        except EOFError:
            self.whitelist = []
        except ValueError:
            self.whitelist = []
        logger.info('Whitelist loaded')

    def save_whitelist(self, filename):
        """
        Saves whitelist to file `filename`.
        """
        with open(filename, 'w', encoding='utf-8') as whitelist_file:
            for whitelist_item in self.whitelist:
                whitelist_file.write(str(whitelist_item) + "\n")

    def is_admin(self, user_id):
        """
        Returns `True` if user with ID `user_id` is administrator,
        otherwise `False`.
        """
        if user_id < 0:
            return True
        return user_id in self.admins

    def is_in_whitelist(self, user_id):
        """
        Returns `True` if user with ID `user_id` is in whitelist,
        otherwise `False`.
        """
        if self.is_admin(user_id):
            return True
        return user_id in self.whitelist

    def load_data(self, filename):
        """
        Tries to load booking data from file `filename`,
        returns None on any error.
        """
        logger.info('Loading data...')
        try:
            with open(filename, 'r', encoding='utf-8') as data_file:
                return json.load(data_file)
        except Exception:  # TODO
            return None
        logger.info('Data loaded')

    @staticmethod
    def init_data():
        """
        Initializes new empty booking data.
        """
        return []

    def load_or_init_data(self, filename):
        """
        Loads booking data from file `filename` and returns it,
        or initializes new data if an error occurred
        while loading data from file.
        """
        if filename is not None:
            self.booking_data = self.load_data(filename)
            if self.booking_data is None:
                self.booking_data = self.init_data()
        else:
            self.booking_data = self.init_data()

    def save_data(self, filename):
        """
        Saves booking data to file `filename`.
        """
        self.booking_data.sort(
            key=lambda booking_data_item: booking_data_item[0])
        with open(filename, 'w', encoding='utf-8') as data_file:
            json.dump(self.booking_data, data_file)

    def save_all_data(self, user_id, data_filename, whitelist_filename):
        """
        Command function.
        Saves booking data to file `data_filename` and whitelist to file
        `whitelist_filename`.
        If user with ID `user_id` do not have permissions to request
        this action, it will not be performed and `BotNoAccess` will be
        raised.
        """
        if not self.is_admin(user_id):
            raise BotNoAccess()
        self.save_data(data_filename)
        self.save_whitelist(whitelist_filename)

    def is_free_time(self, time_data, duration):
        """
        Checks whether time starting from `time_data` with duration
        `duration` is free (not intersecting with any other booking
        items).
        If it is free, `True` is returned, otherwise `False`.
        Important notice: is start time of some item is equal to
        end time of another item, this is not considered intersection.
        """
        # TODO: probably optimize this code
        for booking_data_item in self.booking_data:
            if booking_data_item[0] == time_data:
                return False
            if ((booking_data_item[0] < (time_data + duration))
                    and ((booking_data_item[0] + booking_data_item[1])
                         > time_data)):
                return False
        return True

    def book(self, user_id, time_data, duration, description):
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
        if not self.is_in_whitelist(user_id):
            raise BotNoAccess()
        if not self.is_free_time(time_data, duration):
            raise BotTimeOccupied()
        if time_data <= (datetime.now() - TIME_AXIS).total_seconds():
            raise BotTimePassed()
        self.booking_data.append([time_data, duration, description, user_id])
        self.booking_data.sort(
            key=lambda booking_data_item: booking_data_item[0])

    def get_booking(self, time_data):
        """
        Returns array index of booking item which intersects with time
        `time_data`.
        If such item is not found, `-1` is returned.
        """
        for i in range(len(self.booking_data)):
            booking_data_item = self.booking_data[i]

            if booking_data_item[0] == time_data:
                return i
            if ((booking_data_item[0] < (time_data))
                    and ((booking_data_item[0] + booking_data_item[1])
                         > time_data)):
                return i
        return -1

    def unbook(self, user_id, time_data, force=False):
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
        if not self.is_in_whitelist(user_id):
            raise BotNoAccess()
        if force:
            if not self.is_admin(user_id):
                raise BotNoAccess()
        if not force:
            if time_data <= (datetime.now() - TIME_AXIS).total_seconds():
                raise BotTimePassed()
        booking_id = self.get_booking(time_data)
        if booking_id < 0:
            raise BotBookingNotFound()
        if not force:
            if self.booking_data[booking_id][3] != user_id:
                raise BotNoAccess()
        self.booking_data.pop(booking_id)
        self.booking_data.sort(
            key=lambda booking_data_item: booking_data_item[0])

    def get_timetable(self, user_id, start_time_data=-1, end_time_data=-1):
        """
        Returns timetable, list of booking items starting from
        `start_time_data` (or from the beginning if `start_time_data` is
        less than 0) and ending on `end_time_data` (or not ending if
        `end_time_data` is less than 0).
        """
        result = []
        for booking_data_item in self.booking_data:
            if start_time_data >= 0:
                if (booking_data_item[0] + booking_data_item[1]
                        < start_time_data):
                    continue
            if end_time_data >= 0:
                if booking_data_item[0] > end_time_data:
                    continue
            result += [booking_data_item]
        return result


def process_date(date_str):
    """
    Parses date data from given date string `date_str` and returns
    number of seconds between that date and `TIME_AXIS`
    (1970-01-01 00:00).
    `date_str` could be in formats `YYYY-MM-DD`, `DD.MM.YYYY`, `MM-DD`
    or `DD.MM`.
    """
    global minute_treshold
    try:
        result = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            result = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            try:
                result = datetime.strptime(date_str, "%m-%d")
            except ValueError:
                result = datetime.strptime(date_str, "%d.%m")

    if result.year == 1900:
        result = datetime(
            datetime.today().year, result.month, result.day)
    return int((result - TIME_AXIS).total_seconds())


def process_date_time(date_str, time_str):
    """
    Parses date and time data from given date string `date_str`
    and time string `time_str` and returns number of seconds
    between that moment and `TIME_AXIS` (the 1970-01-01 00:00).
    `date_str` could be in formats `YYYY-MM-DD`, `DD.MM.YYYY`, `MM-DD`
    or `DD.MM`.
    `time_str` could be in formats `hh:mm` or `hh:mm:ss`.
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
    `time_str` could be in formats `minutes:seconds` or simply
    `seconds`.
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
