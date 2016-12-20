# -*- coding: utf-8 -*-
import json
from datetime import *
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
TIME_PASSED = 5
BOOKING_NOT_FOUND = 6
MISC_ERROR = -1

minute_treshold = 15
time_axis = datetime(1970, 1, 1)

def load_admins(filename):
    global admins
    try:
        with open(filename, 'r', encoding="utf-8") as admins_file:
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
        log('EOF error in admin list file', 'ERROR')
    except ValueError:
        log('Format error in admin list file', 'ERROR')
    except Exception:
        log('Misc error in admin list file', 'ERROR')

def load_whitelist(filename):
    global whitelist
    try:
        with open(filename, 'r', encoding="utf-8") as whitelist_file:
            for line in whitelist_file:
                data = line.strip()
                if len(data) == 0:
                    continue
                if data[0] == '#':
                    continue
                whitelist += [int(data)]
    except Exception:
        whitelist = []
        log('Error in whitelist file, whitelist set empty',)

def save_whitelist(filename):
    global whitelist
    try:
        with open(filename, 'w', encoding="utf-8") as whitelist_file:
            for whitelist_item in whitelist:
                whitelist_file.write(str(whitelist_item) + "\n")
    except FileNotFoundError:
        log('Can not find whitelist file', 'ERROR')
    except BufferError:
        log('Buffer error in whitelist file', 'ERROR')
    except EOFError:
        log('EOF error in whitelist file', 'ERROR')
    except ValueError:
        log('Format error in whitelist file', 'ERROR')
    except Exception:
        log('Misc error in whitelist file', 'ERROR')

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
        with open(filename, 'r', encoding="utf-8") as data_file:
            return json.load(data_file)
    except Exception:
        return None

def init_data():
    booking_data = []
    return booking_data

def load_data(filename):
    global booking_data
    booking_data = load_data_from_file(filename)
    if booking_data == None:
        booking_data = init_data()

def save_data(user_id, filename, whitelist_filename):
    global booking_data
    if not is_admin(user_id):
        return NO_ACCESS
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])
    with open(filename, 'w', encoding="utf-8") as data_file:
        json.dump(booking_data, data_file)
    save_whitelist(whitelist_filename)
    return EVERYTHING_OK

def is_free_time(time_data, duration):
    global booking_data
    for booking_data_item in booking_data:
        if booking_data_item[0] == time_data:
            return False
        if (booking_data_item[0] < (time_data + duration)) and ((booking_data_item[0] + booking_data_item[1]) > time_data):
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
    if time_data <= (datetime.now() - time_axis).total_seconds():
        return TIME_PASSED
    booking_data += [[time_data, duration, description, user_id]]
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])
    return EVERYTHING_OK

def get_booking(time_data):
    global booking_data
    for i in range(len(booking_data)):
        booking_data_item = booking_data[i]

        if booking_data_item[0] == time_data:
            return i
        if (booking_data_item[0] < (time_data)) and ((booking_data_item[0] + booking_data_item[1]) > time_data):
            return i
    return -1

def unbook(user_id, time_data, force=False):
    global booking_data
    if not is_in_whitelist(user_id):
        return NO_ACCESS
    if force:
        if not is_admin(user_id):
            return NO_ACCESS
    if not force:
        if time_data <= (datetime.now() - time_axis).total_seconds():
            return TIME_PASSED
    booking_id = get_booking(time_data)
    if booking_id < 0:
        return BOOKING_NOT_FOUND
    if not force:
        if booking_data[booking_id][3] != user_id:
            return NO_ACCESS
    booking_data.pop(booking_id)
    booking_data.sort(key=lambda booking_data_item: booking_data_item[0])
    return EVERYTHING_OK

def get_timetable(user_id, start_time_data=-1, end_time_data=-1):
    global booking_data
    result = [EVERYTHING_OK]
    for booking_data_item in booking_data:
        if start_time_data >= 0:
            if (booking_data_item[0] + booking_data_item[1]) < start_time_data:
                continue
        if end_time_data >= 0:
            if booking_data_item[0] > end_time_data:
                continue
        result += [booking_data_item]
    return result

def process_date_time(date_str, time_str):
    global minute_treshold
    try:
        data_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            data_date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            try:
                data_date = datetime.strptime(date_str, "%m-%d")
            except ValueError:
                data_date = datetime.strptime(date_str, "%d.%m")
    try:
        data_time = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        data_time = datetime.strptime(time_str, "%H:%M:%S")

    result = datetime.combine(data_date.date(), data_time.time())
    if result.year == 1900:
        result = datetime(datetime.today().year, result.month, result.day, result.hour, (result.minute // minute_treshold) * minute_treshold)
    else:
        result = datetime(result.year, result.month, result.day, result.hour, (result.minute // minute_treshold) * minute_treshold)
    return int((result - time_axis).total_seconds())

def process_time(time_str):
    if len(time_str.split(":")) == 1:
        data_timedelta = timedelta(minutes=((int(time_str) // minute_treshold) * minute_treshold))
    else:
        time_str_tokens = time_str.split(":")
        data_timedelta = timedelta(hours=((int(time_str_tokens[0]) // minute_treshold) * minute_treshold), minutes=((int(time_str_tokens[1]) // minute_treshold) * minute_treshold))

    return int(data_timedelta.total_seconds())
