# -*- coding: utf-8 -*-


class BotCommandException(Exception):
    """
    Base exception for errors which occurs while executing commands
    and should be reported to user (normally this should only include
    errors which occurs because of incorrect user data or incorrect
    bot settings).
    """
    pass


class BotBadDateFormat(BotCommandException):
    """
    Invalid date format.
    """
    pass


class BotNoAccess(BotCommandException):
    """
    User do not have access (permissions) to use some command or do
    some action.
    """
    pass


class BotBadInput(BotCommandException):
    """
    Invalid user input.
    """
    pass


class BotTimeOccupied(BotCommandException):
    """
    Booking time is already occupied by other booking item.
    """
    pass


class BotTimePassed(BotCommandException):
    """
    Booking time has already passed and user could not create booking
    item in the past time.
    """
    pass


class BotBookingNotFound(BotCommandException):
    """
    Failed to find booking item with given parameters.
    """
    pass


class BotUsernameNotFound(BotCommandException):
    """
    Failed to find user with such username (or such user has not started
    dialog with bot yet).
    """
    pass
