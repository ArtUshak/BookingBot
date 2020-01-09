# -*- coding: utf-8 -*-
"""Settings for bot."""
import logging
import os
from typing import Optional, List, Tuple


log_file: str = os.environ.get('BOT_LOG', default='../BookingBot-data/log.log')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s',
                    handlers=[logging.FileHandler(log_file),
                              logging.StreamHandler()])

min_year = 1970

message_bad_cmd = ('Команда не найдена. Для получения списка команд введите '
                   '/help.')
message_indev = 'Данная функция находится в разработке.'
message_testing = ('Бот в процессе тестирования. '
                   'Приносим извинения за неудобства.')
message_operation_ok = 'Операция успешно произведена.'
message_bad_input = 'Некорректный запрос.'
message_bad_date_format = 'Некорректно введена дата.'
message_no_access = 'Нет доступа.'
message_misc_error = 'Неизвестная ошибка.'
message_time_occupied = 'Время занято.'
message_time_passed = 'Время уже прошло.'
message_booking_not_found = 'Событие не найдено.'
message_date_empty = 'Нет событий на указанную дату.'
message_username_not_found = ('Пользователь с таким именем не найден. Возможно'
                              ' он ещё не начал диалог с ботом.')

message_input_date = 'Введена дата {}'

message_timetable_header = 'Расписание:'
message_timetable_date_row = 'День {}'
message_timetable_row = '{} - {}: {}'

message_whitelist_header = 'Белый список:'
message_whitelist_row = '{1} (ID {0})'

cmd_text_timetable = 'Получить расписание'
cmd_text_timetable_today = 'Получить на сегодня'
cmd_text_timetable_date = 'Получить на дату'
cmd_text_timetable_book = 'Забронировать аудиторию'
cmd_text_timetable_unbook = 'Отменить бронирование'
cmd_text_contactlist = 'Контакты'
cmd_text_help = 'Справка'

message_prompt_date = 'Введите дату через календарь:'
message_book_1 = 'Введите время начала события в формате часы:минуты'
message_book_2 = ('Введите длительность события в формате часы:минуты или'
                  ' минуты')
message_book_3 = 'Введите описание события:'
message_unbook_1 = 'Выберите событие:'

contactlist_file: str = os.environ.get(
    'CONTACTLIST_FILE',
    default=os.path.join('..', 'BookingBot-data', 'contacts.txt')
)
help_file = 'help.txt'

token = os.environ.get('TOKEN')

proxy_str: Optional[str] = os.environ.get('TELEGRAM_PROXY')
proxy_data: Optional[List[str]] = None
if (proxy_str is not None) and (proxy_str != 'none'):
    proxy_data = proxy_str.split()[:2]

database_url: str = os.environ.get(
    'DATABASE_URL', default='sqlite:/../BookingBot-data/data.db'
)

calendar_locale_str: Optional[str] = os.environ.get('BOT_CALENDAR_LOCALE')
calendar_locale: Optional[Tuple[Optional[str], Optional[str]]] = None
if calendar_locale_str is not None:
    calendar_locale_tokens: List[str] = calendar_locale_str.split('.')
    calendar_locale = (calendar_locale_tokens[0], calendar_locale_tokens[1])

thread_number_str: Optional[str] = os.environ.get('THREAD_NUMBER')
thread_number: int = 2
if thread_number_str is not None:
    thread_number = int(thread_number_str)
