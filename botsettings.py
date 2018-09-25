# -*- coding: utf-8 -*-
"""Settings for bot."""
import locale
import logging

import telebot


log_file = '../BookingBot-data/log.log'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s',
                    handlers=[logging.FileHandler(log_file),
                              logging.StreamHandler()])

locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF8',))

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

message_prompt_date = 'Введите дату через календарь'
message_book_1 = 'Введите время начала события в формате часы:минуты'
message_book_2 = ('Введите длительность события в формате часы:минуты или'
                  ' минуты')
message_book_3 = 'Введите описание события'
message_unbook_1 = 'Введите время события в формате часы:минуты'

contactlist_file = '../BookingBot-data/contacts.txt'
help_file = 'help.txt'
data_file = '../BookingBot-data/booking.json'
whitelist_file = '../BookingBot-data/whitelist.txt'
adminlist_file = '../BookingBot-data/admins.txt'
token_file = '../BookingBot-data/b1540-n38-token.txt'
proxy_file = '../BookingBot-data/proxy.txt'
user_data_file = '../BookingBot-data/users.json'
