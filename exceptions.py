# -*- coding: utf-8 -*-
"""Exceptions, specific to bot."""


class BotCommandException(Exception):
    """
    Base exception for all bot errors.

    Base exception for errors which occurs while executing commands
    and should be reported to user (normally this should only include
    errors which occurs because of incorrect user data or incorrect
    bot settings).
    """

    pass


class BotBadDateFormat(BotCommandException):
    """Invalid date format."""

    pass


class BotNoAccess(BotCommandException):
    """
    No access.

    User do not have access (permissions) to use some command or do
    some action.
    """

    pass


class BotBadInput(BotCommandException):
    """Invalid user input."""

    pass


class BotTimeOccupied(BotCommandException):
    """Booking time is already occupied by other booking item."""

    pass


class BotTimePassed(BotCommandException):
    """
    Invalid booking time.

    Booking time has already passed and user could not create booking
    item in the past time.
    """

    pass


class BotBookingNotFound(BotCommandException):
    """Failed to find booking item with given parameters."""

    pass


class BotDateEmpty(BotCommandException):
    """Failed to find any booking items for given date."""

    pass


class BotUsernameNotFound(BotCommandException):
    """
    No user with username.

    Failed to find user with such username (or such user has not started
    dialog with bot yet).
    """

    pass
