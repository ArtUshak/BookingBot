# BookingBot

Telegram bot for booking auditorium

See `help.txt` for information about commands (it's in russian, not trasnslated into english yet).

You can also see documentation in python code.

## Configuration

Bot settings (including paths of data files) should be set in `botsettings.py` as variables.

### Token file

File name should be set in variable `token_file`.

This is text file with token for Telegram API on first line (leading and traling spaces are ignored).

*Important notice*: this data should be kept private for security reasons.

### Contact list file

File name should be set in variable `contactlist_file`.

This is text file, its content will be displayed to users who type `/contactlist` command.

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

### Database

Database filename should be set in variable `database_file` (SQLite database are only supported yet).

### Log file

File name should be set in variable `log_file`.

Log will be appended to this file.

## Management

Management script is named `manage.py`.

### Loading whitelist file

Whitelist can be added to database from file using following command:

```sh
python ./manage.py load-whitelist FILENAME
```

Each line of file should contain either user ID of user, or comment, beggining with the # character.

Example:

```text
#This is whitelist
252070907
#124889533
```

### Loading administrator list file

Administrators can be added from file using following command:

```sh
python ./manage.py load-admins FILENAME
```

Each line of file should contain either user ID of amdministrator, or comment, beggining with the # character.

Example:

```text
#This is admin list
252070907
#124889533
```

### Adding administrator

User can be made administator using following command:

```sh
python ./manage.py op-username USERNAME
```

### Removing administrator

User can be made not administator using following command:

```sh
python ./manage.py deop-username USERNAME
```
