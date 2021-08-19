# notifier
Wikidot notifications

# Usage

## Installation

Requires at least Python 3.8.

Via [Poetry](https://python-poetry.org/):

```shell
poetry install
```

## Authentication

notifier requires authentication in order to access its Wikidot account and
its gmail account.

To set the authentication, open a Python shell:

```shell
poetry run python3
```

Then in the Python shell execute the following:

```python
import keyring
keyring.set_password("yagmail", GMAIL_USERNAME, GMAIL_PASSWORD)
keyring.set_password("wikidot", WIKIDOT_USERNAME, WIKIDOT_PASSWORD)
```

The usernames must be the same as those defined in the config file.

Authentication only needs to be performed once. It will need to be
re-performed if the passwords change or when e.g. moving to a new host.

## Execution

To start the task runner:

```shell
poetry run python3 -m notifier path_to_config_file
```

The standard config file is `config.toml`.

# Development

Run tests:

```shell
poetry run python3 -m pytest
```

Lint:

```shell
poetry run pylint notifier
```

