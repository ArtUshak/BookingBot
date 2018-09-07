# -*- coding: utf-8 -*-
import logging

import telebot


log_file = '../BookingBot-data/log.log'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(message)s',
                    handlers=[logging.FileHandler(log_file),
                              logging.StreamHandler()])


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

message_timetable_header = 'Расписание:'
message_timetable_date_row = 'День {}'
message_timetable_row = '{} - {}: {}'

cmd_text_timetable = 'Получить расписание'
cmd_text_timetable_today = 'Получить на сегодня'
cmd_text_timetable_book = 'Забронировать аудиторию'
cmd_text_timetable_unbook = 'Отменить бронирование'
cmd_text_contactlist = 'Контакты'


contactlist_file = '../BookingBot-data/contacts.txt'
help_file = 'help.txt'
data_file = '../BookingBot-data/booking.json'
whitelist_file = '../BookingBot-data/whitelist.txt'
adminlist_file = '../BookingBot-data/admins.txt'
token_file = '../BookingBot-data/b1540-n38-token.txt'
proxy_file = '../BookingBot-data/proxy.txt'
user_data_file = '../BookingBot-data/users.json'
