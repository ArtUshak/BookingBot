# -*- coding: utf-8 -*-
"""ORM models for bot data."""
from datetime import date
import logging

import peewee

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

    def next_month(self):
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

    def create_input_calendar(self, date_data: date):
        """Create calendar for inputting date."""
        assert(self.input_calendar is None)
        self.input_calendar = InputCalendar.create(
            year=date_data.year, month=date_data.month
        )
        self.save()

    def start_input_line_book(self):
        """Start input line for creating new booking item (event)."""
        self.clear_input_line()
        self.input_line_book = InputLineBook.create(
            start_date=None, start_time=None, duration_seconds=None
        )
        self.input_line_type = 'BOOK'
        self.create_input_calendar(date.today())
        self.save()

    def start_input_line_unbook(self):
        """Start input line for removing booking item (event)."""
        self.clear_input_line()
        self.input_line_unbook = InputLineUnbook.create(
            start_date=None
        )
        self.input_line_type = 'UNBOOK'
        self.create_input_calendar(date.today())
        self.save()

    def start_input_line_timetable_date(self):
        """Start input line for getting timetable."""
        assert(self.input_line_type is None)
        self.input_line_type = 'TIMETABLE_DATE'
        self.create_input_calendar(date.today())
        self.save()

    def clear_input_line(self):
        """Clear input line."""
        if self.input_line_book is not None:
            self.input_line_book.delete_instance()
            self.input_line_book = None
        if self.input_line_unbook is not None:
            self.input_line_unbook.delete_instance()
            self.input_line_unbook = None
        if self.input_calendar is not None:
            self.input_calendar.delete_instance()
            self.input_calendar = None
        self.input_line_type = None
        self.save()

    def input_date_next_month(self):
        """Move calendar input date to next month."""
        assert(self.input_calendar is not None)
        self.input_calendar.next_month()
        self.input_calendar.save()

    def input_date_previous_month(self):
        """Move calendar input date to previous month."""
        assert(self.input_calendar is not None)
        self.input_calendar.previous_month()
        self.input_calendar.save()

    class Meta:
        """Metadata."""

        database = db_proxy
        constraints = [
            peewee.Check(
                ('((input_line_type = "BOOK")'
                 'AND (input_line_book IS NOT NULL))'
                 'OR ((input_line_type != "BOOK")'
                 'AND (input_line_book IS NULL))')
            ),
            peewee.Check(
                ('((input_line_type = "UNBOOK")'
                 'AND (input_line_unbook IS NOT NULL))'
                 'OR ((input_line_type != "UNBOOK")'
                 'AND (input_line_unbook IS NULL))')
            ),
            peewee.Check(
                ('((input_line_type IS NULL)'
                 'AND (input_calendar IS NULL))'
                 'OR (input_line_type IS NOT NULL)')
            )]


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


def db_init(database_filename: str):
    """Initialize database connection."""
    logger.info('Initializing database connection...')
    db_proxy.initialize(
        peewee.SqliteDatabase(database_filename))
    db_proxy.connect()
    db_proxy.create_tables(model_list)
    logger.info('Database connection initialized')
