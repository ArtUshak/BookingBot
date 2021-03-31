# BookingBot

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/1b958e1c7a664b6a93270dc8c1f7534b)](https://app.codacy.com/app/ArtUshak/BookingBot?utm_source=github.com&utm_medium=referral&utm_content=ArtUshak/BookingBot&utm_campaign=Badge_Grade_Dashboard)

Telegram bot for booking auditorium

See `help.txt` for information about commands (it is in russian, not trasnslated into english yet).

You can also see documentation in python code.

## Configuration

Bot settings should be set as environment variables.

### Token

Environment variable `TOKEN` should be set to token for Telegram API.

*Important notice*: this data should be kept private for security reasons.

### Contact list file

Environment variable `CONTACTLIST_FILE` should be set to name of contact list file, default value is `../BookingBot-data/contacts.txt`.

This is text file, its content will be displayed to users who type `/contactlist` command.

### Proxy file

Environment variable `TELEGRAM_PROXY` should be set to proxy configuration.

It should contain proxy type, space character and proxy URL.

Example:

```sh
export TELEGRAM_PROXY="https https://192.168.0.228:8080"
```

Or, if no proxy should be used:

```sh
export TELEGRAM_PROXY=none
```

### Database

Environment variable `DATABASE_URL` should be set to database URL (see [playhouse.db_url.connect documentation](http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#connect)), default value is `sqlite:/../BookingBot-data/data.db`.

Example:

```sh
export DATABASE_URL="postgresql://bookingbot:password@localhost:5432/bookingbot"
```

Or:

```sh
export DATABASE_URL="sqlite:/../BookingBot-data/data.db"
```

### Log file

Environment variable `BOT_LOG` should be set to log file name, default value is `../BookingBot-data/log.log`.

Log will be appended to this file.

### Calendar locale

Environment variable `BOT_CALENDAR_LOCALE` should be set to locale used for rendering calendar, if it is not set, system locale is used.

Example:

```sh
export BOT_CALENDAR_LOCALE=ru_RU.UTF-8
```

### Thread count

Environment variable `THREAD_NUMBER` should be set to thread count for bot, default value is `2`.

Example:

```sh
export THREAD_NUMBER=8
```

## Management

Management script is named `manage.py`.

### Loading whitelist file

Whitelist can be added to database from file using following command:

```sh
python ./manage.py load-whitelist FILENAME
```

Each line of file should contain either user ID of user, or comment, begining with the # character.

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

Each line of file should contain either user ID of amdministrator, or comment, begining with the # character.

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
