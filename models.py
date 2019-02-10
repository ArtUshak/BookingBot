# -*- coding: utf-8 -*-
"""ORM models for bot data."""
from datetime import date
import logging
from typing import List

import peewee
import playhouse.db_url

from botsettings import min_year

logger = logging.getLogger('bot')

db_proxy = peewee.Proxy()


class InputLineBook(peewee.Model):
    """Input line for creating new booking item (event)."""

    start_date = peewee.DateField(null=True)
    start_time = peewee.TimeField(null=True)
    duration_seconds = peewee.IntegerField(null=True)

    class Meta:
        """Metadata."""

        database = db_proxy


class InputLineUnbook(peewee.Model):
    """Input line for removing booking item (event)."""

    start_date = peewee.DateField(null=True)

    class Meta:
        """Metadata."""

        database = db_proxy


class InputCalendar(peewee.Model):
    """Calendar input data."""

    year = peewee.IntegerField()
    month = peewee.IntegerField()

    def next_month(self) -> None:
        """Move input date to next month."""
        self.month += 1
        if self.month > 12:
            self.year += 1
            self.month = 1
        self.save()

    def previous_month(self) -> bool:
        """
        Move input date to previous month.

        Return `True` if date was changed, `False` if date
        could not be changed earliest year is reached.
        """
        self.month -= 1
        if self.month < 1:
            if self.year <= min_year:
                self.month += 1
                return False
            self.year -= 1
            self.month = 12
        self.save()
        return True

    class Meta:
        """Metadata."""

        database = db_proxy
        constraints = [
            peewee.Check(
                ('(month >= 1)'
                 'AND (month <= 12)')
            )]


class User(peewee.Model):
    """Telegram bot user."""

    user_id = peewee.BigIntegerField(unique=True)
    chat_id = peewee.BigIntegerField(null=True, index=True)
    username = peewee.CharField(max_length=32, null=True, index=True)

    is_admin = peewee.BooleanField(default=False)
    is_whitelisted = peewee.BooleanField(default=False)

    input_calendar = peewee.ForeignKeyField(
        InputCalendar, backref='user', null=True, default=None,
        db_column='input_calendar')
    input_line_book = peewee.ForeignKeyField(
        InputLineBook, backref='user', null=True, default=None,
        db_column='input_line_book')
    input_line_unbook = peewee.ForeignKeyField(
        InputLineUnbook, backref='user', null=True, default=None,
        db_column='input_line_unbook')
    input_line_type = peewee.CharField(
        choices=[('BOOK', 'BOOK'), ('UNBOOK', 'UNBOOK'),
                 ('TIMETABLE_DATE', 'TIMETABLE_DATE')],
        null=True, default=None)

    def get_is_admin(self) -> bool:
        """
        Check whether user is administrator.

        Return `True` if user is administrator, otherwise `False`.
        """
        if self.user_id < 0:
            return True
        return self.is_admin

    def get_is_in_whitelist(self) -> bool:
        """
        Check whether user is in whitelist.

        Return `True` if user is in whitelist, otherwise `False`.
        """
        return self.get_is_admin() or self.is_whitelisted

    def create_input_calendar(self, date_data: date) -> None:
        """Create calendar for inputting date."""
        old_input_calendar = self.input_calendar
        self.input_calendar = InputCalendar.create(
            year=date_data.year, month=date_data.month
        )
        self.save()
        if old_input_calendar is not None:
            old_input_calendar.delete_instance()

    def start_input_line_book(self) -> None:
        """Start input line for creating new booking item (event)."""
        self.clear_input_line()
        self.input_line_book = InputLineBook.create(
            start_date=None, start_time=None, duration_seconds=None
        )
        self.input_line_type = 'BOOK'
        self.create_input_calendar(date.today())
        self.save()

    def start_input_line_unbook(self) -> None:
        """Start input line for removing booking item (event)."""
        self.clear_input_line()
        self.input_line_unbook = InputLineUnbook.create(
            start_date=None
        )
        self.input_line_type = 'UNBOOK'
        self.create_input_calendar(date.today())
        self.save()

    def start_input_line_timetable_date(self) -> None:
        """Start input line for getting timetable."""
        self.clear_input_line()
        self.input_line_type = 'TIMETABLE_DATE'
        self.create_input_calendar(date.today())
        self.save()

    def clear_input_line(self) -> None:
        """Clear input line."""
        objects_to_delete: List[peewee.Model] = []
        if self.input_line_book is not None:
            objects_to_delete.append(self.input_line_book)
            self.input_line_book = None
        if self.input_line_unbook is not None:
            objects_to_delete.append(self.input_line_unbook)
            self.input_line_unbook = None
        if self.input_calendar is not None:
            objects_to_delete.append(self.input_calendar)
            self.input_calendar = None
        self.input_line_type = None
        self.save()
        for obj in objects_to_delete:
            obj.delete_instance()

    def input_date_next_month(self) -> None:
        """Move calendar input date to next month."""
        if self.input_calendar is None:
            raise AssertionError()
        self.input_calendar.next_month()
        self.input_calendar.save()

    def input_date_previous_month(self) -> None:
        """Move calendar input date to previous month."""
        if self.input_calendar is None:
            raise AssertionError()
        self.input_calendar.previous_month()
        self.input_calendar.save()

    class Meta:
        """Metadata."""

        database = db_proxy


class BookingItem(peewee.Model):
    """Booking item (event)."""

    start_datetime = peewee.DateTimeField(index=True)
    end_datetime = peewee.DateTimeField(index=True)
    user = peewee.ForeignKeyField(User, backref='booking_items')
    description = peewee.TextField()

    class Meta:
        """Metadata."""

        database = db_proxy


model_list = [InputLineBook, InputLineUnbook, InputCalendar, User, BookingItem]


def db_init(database_url: str) -> None:
    """Initialize database connection."""
    logger.info('Initializing database connection...')
    db_proxy.initialize(playhouse.db_url.connect(database_url))
    db_proxy.connect()
    db_proxy.create_tables(model_list)
    logger.info('Database connection initialized')
