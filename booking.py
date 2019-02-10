# -*- coding: utf-8 -*-
"""Classes and functions to store bot data and manage it."""
from datetime import date, datetime, time, timedelta
import logging
from typing import List, Tuple, Optional

from exceptions import (BotNoAccess, BotTimeOccupied, BotTimePassed,
                        BotBookingNotFound, BotUsernameNotFound)
import models


logger = logging.getLogger('bot')

minute_treshold = 5


def update_user_data(user_id: int, chat_id: int, username: str) -> models.User:
    """
    Update user data.

    Update data for user with ID `user_id`, setting `chat_id` and
    `username`.
    """
    try:
        user: models.User = models.User.get(user_id=user_id)
        user.username = username
        user.chat_id = chat_id
        user.save()
        return user
    except models.User.DoesNotExist:
        user = models.User.create(
            user_id=user_id, chat_id=chat_id, username=username)
        return user


def get_user(user_id: int) -> Optional[models.User]:
    """
    Return user by ID.

    Return user object with ID `user_id`, return None if such
    user could not be found.
    """
    try:
        return models.User.get(user_id=user_id)
    except models.User.DoesNotExist:
        return None


def get_user_by_chat_id(chat_id: int) -> Optional[models.User]:
    """
    Return user by chat ID.

    Return user object with chat ID `chat_id`, return None if such
    user could not be found.
    """
    try:
        return models.User.get(chat_id=chat_id)
    except models.User.DoesNotExist:
        return None


def is_free_time(time_data: datetime, duration: timedelta) -> bool:
    """
    Check whether time span is free.

    Check whether time starting from `time_data` with duration
    `duration` is free (not intersecting with any other booking
    items).

    If it is free, `True` is returned, otherwise `False`.

    Important notice: is start time of some item is equal to
    end time of another item, this is not considered intersection.
    """
    booking_items = models.BookingItem.select().where(
        (models.BookingItem.start_datetime < (time_data + duration))
        & (models.BookingItem.end_datetime > time_data)
    )
    return len(booking_items) == 0


def book(user: models.User, time_data: datetime, duration: timedelta,
         description: str) -> None:
    """
    Create booking item.

    Create booking item for user `user``, with time
    `time_data`, duration `duration` and description `description`.

    If user do not have permissions to request this action, it will
    not be performed and `BotNoAccess` will be raised.

    If time span is already occupied (is intersecting with some other
    item), action will not be performed and `BotTimeOccupied` will be
    raised.

    If time has already passed, action will not be performed and
    `BotTimePassed` will be raised.
    """
    if not user.get_is_in_whitelist():
        raise BotNoAccess()
    if time_data <= datetime.now():
        raise BotTimePassed()
    if not is_free_time(time_data, duration):
        raise BotTimeOccupied()
    models.BookingItem.create(
        start_datetime=time_data,
        end_datetime=time_data + duration,
        description=description, user=user
    )


def get_booking(time_data: datetime) -> Optional[models.BookingItem]:
    """
    Get booking for time.

    Return booking item which intersects with time
    `time_data`.

    If such item is not found, `None` is returned.
    """
    try:
        return models.BookingItem.get(
            (models.BookingItem.start_datetime <= time_data)
            & (models.BookingItem.end_datetime >= time_data)
        )
    except models.BookingItem.DoesNotExist:
        return None


def unbook(user: models.User, time_data: datetime,
           force: bool = False) -> None:
    """
    Remove booking for time.

    Remove booking which intersects with time `time_data`.

    If the parameter `force` is set to `True`, removing of past
    bookings or other user's bookings is allowed (if user have right
    permissions).

    If user `user` do not have permissions to request this action,
    it will not be performed and `BotNoAccess` will be raised.

    If time has already passed and `force` parameter is set to
    `False`, action will not be performed and `BotTimePassed` will be
    raised.

    If such booking is not found, action will not be performed and
    `BotBookingNotFound` will be raised.
    """
    if not user.get_is_in_whitelist():
        raise BotNoAccess()
    if force:
        if not user.get_is_admin():
            raise BotNoAccess()

    if not force:
        if time_data <= datetime.now():
            raise BotTimePassed()

    booking_item: Optional[models.BookingItem] = get_booking(time_data)
    if booking_item is None:
        raise BotBookingNotFound()
    if not force:
        if booking_item.user != user:
            raise BotNoAccess()

    booking_item.delete_instance()


def get_timetable(user_id: int, start_time_data: datetime = None,
                  end_time_data: datetime = None) -> List[models.BookingItem]:
    """
    Get timetable for time span.

    Return timetable, list of booking items starting from
    `start_time_data` (or from the beginning if `start_time_data` is
    less than 0) and ending on `end_time_data` (or not ending if
    `end_time_data` is less than 0).
    """
    result = models.BookingItem.select()

    if start_time_data is not None:
        result = result.where(
            models.BookingItem.end_datetime >= start_time_data
        )

    if end_time_data is not None:
        result = result.where(
            models.BookingItem.start_datetime <= end_time_data
        )

    return list(result.order_by(models.BookingItem.start_datetime))


def get_whitelist(user: models.User) -> List[Tuple[int, str]]:
    """
    Command function.

    Return whitelist as list of user names (or `<?>` strings for users
    who are not present in user database).

    If user `user` do not have permissions to request this
    action, it will not be performed and `BotNoAccess` will be
    raised.
    """
    if not user.get_is_admin():
        raise BotNoAccess()
    whitelist_users = models.User.select().where(models.User.is_whitelisted)

    result = []
    for whitelist_user in whitelist_users:
        if whitelist_user.username is not None:
            whitelist_username = (
                '@' + whitelist_user.username)
        else:
            whitelist_username = '<?>'
        result.append((whitelist_user.user_id, whitelist_username,))
    return result


def add_user_to_whitelist(user: models.User, target_username: str) -> None:
    """
    Command function.

    Add user with name `target_username` to whitelist.

    If such user could not be found, `BotUsernameNotFound` will be raised.

    If user `user` do not have permissions to request this
    action, it will not be performed and `BotNoAccess` will be
    raised.
    """
    if user.get_is_admin():
        raise BotNoAccess()
    try:
        models.User.get(
            models.User.username == target_username
        ).update(is_whitelisted=True)
    except models.User.DoesNotExist:
        raise BotUsernameNotFound()


def remove_user_from_whitelist(user: models.User,
                               target_username: str) -> None:
    """
    Command function.

    Remove user with name `target_username` from whitelist.

    If such user could not be found, `BotUsernameNotFound` will be raised.

    If user `user` do not have permissions to request this
    action, it will not be performed and `BotNoAccess` will be
    raised.
    """
    if user.get_is_admin():
        raise BotNoAccess()
    try:
        models.User.get(
            models.User.username == target_username
        ).update(is_whitelisted=False)
    except models.User.DoesNotExist:
        raise BotUsernameNotFound()


def process_date(date_str: str) -> date:
    """
    Parse date from string.

    Parse date data from given date string `date_str` and return
    `datetime.date` object.

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

    return date(result.year, result.month, result.day)


def process_time(time_str: str) -> time:
    """
    Parse time from string.

    Parse time data from given date string `date_str` and return
    `datetime.time` object.

    `time_str` could be in formats `hh:mm` or `hh:mm:ss`.
    """
    global minute_treshold
    try:
        result = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        result = datetime.strptime(time_str, "%H:%M:%S")

    return time(result.hour, result.minute, result.second)


def process_date_time(date_str: str, time_str: str) -> datetime:
    """
    Parse date and time from string.

    Parse date and time data from given date string `date_str` and time
    string `time_str` and return `datetime.datetime` object.

    `date_str` could be in formats `YYYY-MM-DD`, `DD.MM.YYYY`, `MM-DD`
    or `DD.MM`.

    `time_str` could be in formats `hh:mm` or `hh:mm:ss`.
    """
    global minute_treshold
    try:
        result_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            result_date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            try:
                result_date = datetime.strptime(date_str, "%m-%d")
            except ValueError:
                result_date = datetime.strptime(date_str, "%d.%m")
    try:
        result_time = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        result_time = datetime.strptime(time_str, "%H:%M:%S")

    result = datetime.combine(result_date.date(), result_time.time())
    if result.year == 1900:
        result = datetime(
            datetime.today().year, result.month, result.day, result.hour,
            (result.minute // minute_treshold) * minute_treshold)
    else:
        result = datetime(
            result.year, result.month, result.day, result.hour,
            (result.minute // minute_treshold) * minute_treshold)
    return result


def process_timedelta(time_str: str) -> timedelta:
    """
    Parse time duration from string.

    Parse time duration from given time string `time_str` and
    return `datetime.timedelta` object.

    `time_str` could be in formats `minutes:seconds` or simply
    `seconds`.
    """
    if len(time_str.split(":")) == 1:
        result_timedelta = timedelta(
            minutes=((int(time_str) // minute_treshold) * minute_treshold))
    else:
        time_str_tokens = time_str.split(":")
        result_timedelta = timedelta(
            hours=((int(time_str_tokens[0]) // minute_treshold)
                   * minute_treshold),
            minutes=((int(time_str_tokens[1]) // minute_treshold)
                     * minute_treshold))

    if result_timedelta.total_seconds() < 0:
        raise ValueError()

    return result_timedelta
