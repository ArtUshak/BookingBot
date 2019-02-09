# BookingBot

Telegram bot for booking auditorium

See `help.txt` for information about commands (it's in russian, not trasnslated into english yet).

You can also see documentation in python code.

## Configuration

Bot settings should be set as environment variables.

### Token

Environment variable `TOKEN` should be set to token for Telegram API.

*Important notice*: this data should be kept private for security reasons.

### Contact list file

File name should be set in variable `contactlist_file`.

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
