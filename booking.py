import json
import time
from botlog import *

admins = []
whitelist = []
booking_data = None

#Error list
EVERYTHING_OK = 0
BAD_DATE_FORMAT = 1
NO_ACCESS = 2
BAD_INPUT = 3
TIME_OCCUPIED = 4
MISC_ERROR = -1

def load_admins(filename):
    global admins
    try:
        with open(filename) as admins_file:
            for line in admins_file:
                data = line.strip()
                if len(data) == 0:
                    continue
                if data[0] == '#':
                    continue
                admins += [int(data)]
    except FileNotFoundError:
        log('Can not find admin list file', 'ERROR')
    except BufferError:
        log('Buffer error in admin list file', 'ERROR')
    except EOFError:
        log('EOF error in help admin list', 'ERROR')
    except ValueError:
        log('Format error in admin list file', 'ERROR')
    except Exception:
        log('Misc error in admin list file', 'ERROR')

def is_admin(user_id):
    global admins
    if user_id < 0:
        return True
    return user_id in admins

def is_in_whitelist(user_id):
    if is_admin(user_id):
        return True
    global whitelist
    return user_id in whitelist

def load_data_from_file(filename):
    try:
        with open(filename, 'r') as data_file:
            return json.load(data_file)
    except Exception:
        return None

def init_data(init_schema):
    booking_data = []
    return booking_data

def load_data(filename):
    global booking_data
    global init_schema
    booking_data = load_data_from_file(filename)
    if booking_data == None:
        booking_data = init_data(init_schema)

def save_data(user_id, filename):
    global booking_data
    if not is_admin(user_id):
        return NO_ACCESS
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])
    with open(filename, 'w') as data_file:
        json.dump(booking_data, data_file)
    return EVERYTHING_OK

def is_free_time(time_data, duration):
    global booking_data
    for booking_data_item in booking_data:
        if (booking_data_item[0] < (time_data + duration)) and ((booking_data_item[0] + booking_data_item[1]) < time_data):
            return False
    return True

def get_is_free_time(time_data, duration):
    return [EVERYTHING_OK, is_free_time(time_data)]

def book(user_id, time_data, duration, description):
    global booking_data
    if not is_in_whitelist(user_id):
        return NO_ACCESS
    if not is_free_time(time_data, duration):
        return TIME_OCCUPIED
    booking_data += [time_data, duration, description]
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])
    return EVERYTHING_OK

minute_treshold = 15

def process_date_time(date_str, time_str):
    global minute_treshold
    try:
        date = time.strptime(time_str, "%Y-%m-%d")
    except ValueError:
        try:
            date = time.strptime(time_str, "%d.%m.%y")
        except ValueError:
            try:
                date = time.strptime(time_str, "%m-%d")
            except ValueError:
                date = time.strptime(time_str, "%d.%m")
    try:
        time = time.strptime(date_str, "%H:%M")
    except ValueError:
        try:
            time = time.strptime(time_str, "%H:%M:%S")
        except ValueError:
            try:
                time = time.strptime(time_str, "%M")

def process_time(time_str):
    try:
        time = time.strptime(date_str, "%H:%M")
    except ValueError:
        try:
            time = time.strptime(time_str, "%H:%M:%S")
        except ValueError:
            try:
                time = time.strptime(time_str, "%M")

def get_timetable(user_id, classid, subject, date):
    global booking_data
    result = [EVERYTHING_OK]
    for booking_data_item in booking_data:
        result += [time.localtime(booking_data_item[0]), time.localtime(booking_data_item[1]), booking_data_item[2]]
    return result
