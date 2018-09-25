# BookingBot

Telegram bot for booking auditorium

See `help.txt` for information about commands (it's in russian, not trasnslated into english yet).

You can also see documentation in python code.

## Configuration

Bot settings (including paths of data files) should be set in `botsettings.py` as variables.

### Contact list file

File name should be set in variable `contactlist_file`.

This is text file, its content will be displayed to users who type `/contactlist` command.

### Administrator list file

File name should be set in variable `adminlist_file`.

This is text file with list of administrator user IDs.

Each line should contain either user ID of amdministrator, or comment, beggining with the # character.

Example:

```text
#This is admin list
252070907
#124889533
```

### Token file

File name should be set in variable `token_file`.

This is text file with token for Telegram API on first line (leading and traling spaces are ignored).

*Important notice*: this data should be kept private for security reasons.

### Whitelist file

File name should be set in variable `whitelist_file`.

This is text file with list of administrator user IDs.

Each line should contain either user ID of amdministrator, or comment, beggining with the # character.

*Important notice*: this file will be overwritten when saving all data, and comments will not be kept.

### Proxy file

File name should be set in variable `proxy_file`.

This is text file with proxy server data.

It should contain proxy type, space character and proxy URL.

Example:

```text
https https://192.168.0.228:8080
```

Or, if no proxy should be used:

```text
none
```

### Data file

File name should be set in variable `data_file`.

This is JSON file with booking data. It is saved and loaded by bot. If this file do not exist, it will be generated.

### User data file

File name should be set in variable `user_data_file`.

This is JSON file with user data (user IDs, usernames, etc). It is saved and loaded by bot. If this file do not exist, it will be generated.

### Log file

File name should be set in variable `log_file`.

Log will be appended to this file.
