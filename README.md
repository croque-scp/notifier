# notifier
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

You may be required to set a keyring password. Make sure you keep a record
of it.

The usernames must be the same as those defined in the config file.

Authentication only needs to be performed once. It will need to be
re-performed if the passwords change or when e.g. moving to a new host.

## Execution

To start the task runner:

```shell
poetry run python3 -m notifier path_to_config_file
```

The standard config file is `config.toml`.

Note that the script will immediately ask for the keyring password, which
must be entered in order for it to be able to work.

# Development

Run tests:

```shell
poetry run pytest
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
