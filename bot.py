# -*- coding: utf-8 -*-
import telebot
import pickle
import sys
import traceback
from datetime import *
import booking
from botlog import *

message_bad_cmd = "Команда не найдена. Для получения списка команд введите /help."
message_indev = "Данная функция находится в разработке."
message_operation_ok = "Операция успешно произведена."
message_bad_input = "Некорректный запрос."
message_bad_date_format = "Некорректно введена дата."
message_no_access = "Нет доступа."
message_misc_error = "Неизвестная ошибка."
message_time_occupied = "Время занято."
message_time_passed = "Время уже прошло."
message_booking_not_found = "Событие не найдено."

message_timetable_header = "Расписание:"
message_timetable_row = "%s - %s: %s"

def get_help():
    help_text = ""
    try:
        with open("help.txt") as help_file:
            help_text = help_file.read()
    except FileNotFoundError:
        log("Can not find help file", "ERROR")
    except BufferError:
        log("Buffer error in help file", "ERROR")
    except EOFError:
        log("EOF error in help file", "ERROR")
    return help_text

message_help = get_help()
log("Help message:\n" + message_help)

data_file = "../bookingbot-data/booking.json"

booking.load_data(data_file)
log("Data loaded")

whitelist_file = "../bookingbot-data/whitelist.txt"
booking.load_whitelist(whitelist_file)
log("Whitelist loaded")
log("Whitelist: %s" % str(booking.whitelist))

adminlist_file = "../bookingbot-data/admins.txt"
booking.load_admins(adminlist_file)
log("Admin list loaded")
log("Admins: %s" % str(booking.admins))

def get_token(filename):
    token = None
    try:
        with open(filename) as token_file:
            token = token_file.readline().strip()
    except FileNotFoundError:
        log("Can not find token file", "ERROR")
    except BufferError:
        log("Buffer error in token file", "ERROR")
    except EOFError:
        log("EOF error in token file", "ERROR")
    return token

token = get_token("../bookingbot-data/b1540-n38-token.txt")

bot = telebot.TeleBot(token)

log("Bot created.")

def get_timedelta(seconds):
    return timedelta(days=seconds%3600, seconds=seconds)

def get_datetime(seconds):
    return booking.time_axis + get_timedelta(seconds)

def get_error_message(error_code, if_ok=None):
    if error_code == booking.EVERYTHING_OK:
        if if_ok == None:
            return message_operation_ok
        else:
            return if_ok
    elif error_code == booking.BAD_DATE_FORMAT:
        return message_invalid_classid
    elif error_code == booking.NO_ACCESS:
        return message_no_access
    elif error_code == booking.MISC_ERROR:
        return message_misc_error
    elif error_code == booking.BAD_INPUT:
        return message_bad_input
    elif error_code == booking.TIME_OCCUPIED:
        return message_time_occupied
    elif error_code == booking.TIME_PASSED:
        return message_time_passed
    elif error_code == booking.BOOKING_NOT_FOUND:
        return message_booking_not_found
    else:
        return message_misc_error

def format_timetable(timetable_data):
    result = message_timetable_header + "\n"
    for timetable_item in timetable_data:
        result += message_timetable_row % (get_datetime(timetable_item[0]).strftime("%H:%M"), get_datetime(timetable_item[0] + timetable_item[1]).strftime("%H:%M"), timetable_item[2])
        result += "\n"
    return result

@bot.message_handler(commands=["start", "help"])
def process_cmd_help(message):
    bot.send_message(message.chat.id, message_help)

@bot.message_handler(commands=["book"])
def process_cmd_book(message):
    sender_id = message.from_user.id
    log("Called /book from user %s (%s)" % (sender_id, message.from_user.username))
    if (len(message.text.split()) < 5):
        bot.send_message(message.chat.id, message_bad_input)
        return
    words = message.text.split(" ", 5)
    cmd_result = booking.MISC_ERROR
    try:
        log("Called /book for date %s, time %s, duration %s, description %s" % (words[1], words[2], words[3], words[4]))
        try:
            time = booking.process_date_time(words[1], words[2])
            duration = booking.process_time(words[3])
        except ValueError:
            cmd_result = booking.BAD_INPUT
        else:
            cmd_result = booking.book(sender_id, time, duration, words[4])
        log("/book result is: %s" % cmd_result)
    except Exception as exception:
        log("Error ocurred when executing comand /book", "USERERR")
        log(exception.args, "USERERR")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in lines:
            log(line, "USERERR")
    bot.send_message(message.chat.id, get_error_message(cmd_result))

@bot.message_handler(commands=["unbook"])
def process_cmd_unbook(message):
    sender_id = message.from_user.id
    log("Called /unbook from user %s (%s)" % (sender_id, message.from_user.username))
    if (len(message.text.split()) < 3):
        bot.send_message(message.chat.id, message_bad_input)
        return
    words = message.text.split(" ", 3)
    cmd_result = booking.MISC_ERROR
    try:
        log("Called /unbook for date %s, time %s" % (words[1], words[2]))
        try:
            time = booking.process_date_time(words[1], words[2])
        except ValueError:
            cmd_result = booking.BAD_INPUT
        else:
            cmd_result = booking.unbook(sender_id, time)
        log("/unbook result is: %s" % cmd_result)
    except Exception as exception:
        log("Error ocurred when executing comand /unbook", "USERERR")
        log(exception.args, "USERERR")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in lines:
            log(line, "USERERR")
    bot.send_message(message.chat.id, get_error_message(cmd_result))

@bot.message_handler(commands=["unbook_force"])
def process_cmd_unbook_force(message):
    sender_id = message.from_user.id
    log("Called /unbook_force from user %s (%s)" % (sender_id, message.from_user.username))
    if (len(message.text.split()) < 3):
        bot.send_message(message.chat.id, message_bad_input)
        return
    words = message.text.split(" ", 3)
    cmd_result = booking.MISC_ERROR
    try:
        log("Called /unbook_force for date %s, time %s" % (words[1], words[2]))
        try:
            time = booking.process_date_time(words[1], words[2], force=True)
        except ValueError:
            cmd_result = booking.BAD_INPUT
        else:
            cmd_result = booking.unbook(sender_id, time)
        log("/unbook_force result is: %s" % cmd_result)
    except Exception as exception:
        log("Error ocurred when executing comand /unbook_force", "USERERR")
        log(exception.args, "USERERR")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in lines:
            log(line, "USERERR")
    bot.send_message(message.chat.id, get_error_message(cmd_result))

@bot.message_handler(commands=["timetable"])
def process_cmd_settask(message):
    sender_id = message.from_user.id
    log("Called /timetable from user %s (%s)" % (sender_id, message.from_user.username))
    cmd_result = booking.MISC_ERROR
    try:
        cmd_result_list = booking.get_timetable(sender_id)
        cmd_result = cmd_result_list[0]
    except Exception as exception:
        log("Error ocurred when executing comand /timetable", "USERERR")
        log(exception.args, "USERERR")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in lines:
            log(line, "USERERR")
    timetable = []
    if cmd_result == booking.EVERYTHING_OK:
        timetable = format_timetable(cmd_result_list[1:])
    bot.send_message(message.chat.id, get_error_message(cmd_result, if_ok=timetable))

@bot.message_handler(commands=["savedata"])
def process_cmd_save(message):
    sender_id = message.from_user.id
    log("Called /savedata from user %s (%s)" % (sender_id, message.from_user.username))
    cmd_result = booking.MISC_ERROR
    try:
        cmd_result = booking.save_data(sender_id, data_file, whitelist_file)
        log("/savedata result is: %s" % cmd_result)
    except Exception as exception:
        log("Error ocurred when executing comand /savedata", "USERERR")
        log(exception.args, "USERERR")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in lines:
            log(line, "USERERR")
    bot.send_message(message.chat.id, get_error_message(cmd_result))

@bot.message_handler(commands=["logmyinfo"])
def process_cmd_logmyinfo(message):
    sender_id = message.from_user.id
    log("Called /logmyinfo from user %s (%s)" % (sender_id, message.from_user.username))

"""
@bot.message_handler(content_types=["text"])
def process_input(message):
    log(message.text)
    words = message.text.split()
    log(str(words))
    if len(words) != 2:
        bot.send_message(message.chat.id, message_bad_input)
    else:
        name = words[0]
        lang = words[1]
        if result == None:
            bot.send_message(message.chat.id, "!")
        #else:
            #bot.send_message(message.chat.id, message_output % result)
"""

if __name__ == "__main__":
    bot.polling(none_stop=True)

