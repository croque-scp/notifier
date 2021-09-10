# notifier

[![tests](https://github.com/croque-scp/notifier/actions/workflows/tests.yml/badge.svg)](https://github.com/croque-scp/notifier/actions/workflows/tests.yml)

Wikidot notifications

# Usage

Please note that there should only be one instance of this service running
at once &mdash; any duplication would result in duplicated messages and
would cause spam.

These instructions are provided in case for whatever reason this specific
service is no longer able to operate and/or I am no longer able to maintain
it. Please do not actually attempt to launch another instance of this
service outside of that circumstance.

## Installation

Requires at least Python 3.8.

Via [Poetry](https://python-poetry.org/):

```shell
poetry install
```

## Authentication

notifier requires authentication in order to access its Wikidot account and
its gmail account. [keyring](https://github.com/jaraco/keyring) is used for
securely storing passwords.

You may wish to set up keyring's backend yourself. notifier comes with
[keyrings.cryptfile](https://pypi.org/project/keyrings.cryptfile/)
installed by default.

To set the authentication:

```shell
$ poetry run keyring set wikidot <Wikidot username>
Password: <Wikidot password>

$ poetry run keyring set yagmail <Gmail username>
Password: <Gmail password>
```

The usernames must be the same as those defined in the config file.

If using the MySQL database driver, the database host, username and
password will also need to be set:

```shell
$ poetry run keyring set mysql notifier_host
Password: <MySQL database host>

$ poetry run keyring set mysql notifier_username
Password: <MySQL database username>

$ poetry run keyring set mysql notifier
Password: <MySQL database password>
```

You may be required to set a keyring password. Make sure you keep a record
of it.

Authentication only needs to be performed once. It will need to be
re-performed if the passwords change or when e.g. moving to a new host.

## Database setup

### SQLite

If using the SQLite database driver, no database setup is necessary.

### MySQL

If using the MySQL database driver, MySQL will need to be installed, and a
MySQL server will need to be running somewhere.

A new user will need to be created for the notifier, replacing the
placeholders with the MySQL-specific credentials supplied above:

```sql
CREATE USER '<username>'@'<host>' IDENTIFIED BY '<password>';
```

Create the database, with the database's name matching the name in the
config file (default: `wikidot_notifier`), and grant the new user access to
it:

```sql
CREATE DATABASE `<name>` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin;
GRANT ALL PRIVILEGES ON `<name>`.* TO '<username>'@'<host>';
```

### Other drivers

If using another driver (e.g. a custom one), ensure that it is set up
correctly.

## Execution

To start the notifier:

```shell
poetry run python3 -m notifier path_to_config_file
```

The standard config file is `config.toml`.

Note that the script will immediately ask for the keyring password, which
must be entered in order for it to be able to work.

# Development

Run tests:

```shell
poetry run pytest --notifier-config path_to_config_file
```

Produce a sample digest and print it to stdout, where `[lang]` is the code
of any supported language and `[method]` is either `pm` or `email`:

```shell
poetry run python3 tests/make_sample_digest.py [lang] [method]
```

Lint:

```shell
poetry run pylint notifier
poetry run black notifier
```

Typecheck:

```shell
poetry run mypy notifier
```
