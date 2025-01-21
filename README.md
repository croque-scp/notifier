# Wikidot Notifications

[![tests](https://github.com/croque-scp/notifier/actions/workflows/tests.yml/badge.svg)](https://github.com/croque-scp/notifier/actions/workflows/tests.yml)

This is the open-source codebase for [Wikidot Notifications](https://notifications.wikidot.com?utm_source=github&utm_medium=referral&utm_campaign=ghreadme), a cloud service providing forum notifications for sites on Wikidot.

This notifications service searches for new forum posts on Wikidot and delivers notifications for users that are subscribed to them via email or Wikidot private message. Manual subscriptions as well as a set of rules defining 'automatic subscriptions' are supported. Notifications can be delivered in [several languages](https://notifications.wikidot.com/faq#languages?utm_source=github&utm_medium=referral&utm_campaign=ghreadme) contributed by members of the Wikidot community.

This service is operated and developed by Wikidot user Croquembouche and is not associated with Wikidot Inc. or any particular site hosted on Wikidot other than [notifications.wikidot.com](https://notifications.wikidot.com?utm_source=github&utm_medium=referral&utm_campaign=ghreadme).

See also:

* [Documentation](https://notifications.wikidot.com/faq?utm_source=github&utm_medium=referral&utm_campaign=ghreadme)
* [Status page](https://notifications.wikidot.com/status?utm_source=github&utm_medium=referral&utm_campaign=ghreadme)
* [List of supported Wikidot sites](https://notifications.wikidot.com/wikis?utm_source=github&utm_medium=referral&utm_campaign=ghreadme)
* [List of subscribed users](https://notifications.wikidot.com/users?utm_source=github&utm_medium=referral&utm_campaign=ghreadme)
* If you are a user, [your user configuration](https://notifications.wikidot.com/redirect-to-your-config?utm_source=github&utm_medium=referral&utm_campaign=ghreadme)

The notifications service is written in Python and runs on AWS Lambda using a MySQL database on AWS EC2.

# Usage

> [!WARNING]
> **There must only be one instance of this service active.** Duplication would result in duplicated messages and would cause spam.
> 
> The instructions below are provided in case this specific service is no longer able to operate and/or I am no longer able to maintain it. Do not attempt to launch another instance of this service outside of that circumstance.

## Installation

### With Docker

Requires Docker.

The Dockerfile specifies a number of stages. For local testing, set the target stage to 'execute':

```shell
docker build --target execute --tag notifier:latest .
```

### Locally

Requires at least Python 3.8.

Via [Poetry](https://python-poetry.org/):

```shell
poetry install
```

## Authentication

In addition to the config file based on the one provided in this repository, notifier requires an additional authentication file to provide passwords etc. for the various services it needs.

See [docs/auth.md](/docs/auth.md) for more information and instructions.

## Database setup

For local development and testing, notifier requires a MySQL database. See [docs/database.md](/docs/database.md) for more information and instructions.

## Local execution

To start the notifier service in a Docker container:

```shell
docker run --rm notifier:latest path_to_config_file path_to_auth_file
```

Or locally:

```shell
poetry run python3 -m notifier path_to_config_file path_to_auth_file
```

Or with Docker:

```shell
docker build --target execute --tag notifier:execute .
docker run --rm notifier:execute path_to_config_file path_to_auth_file
```

The config file that my notifier instance uses is `config/config.toml`. A
sample auth file with dummy secrets, used for CI tests, can be found at
`config/auth.ci.toml`.

The service will run continuously and activate an automatically-determined
set of notification channels each hour.

To activate an automatically-determined set of channels immediately and
once only, add the `--execute-now` switch with no parameter. Note that this
must be run during the first minute of an hour to match any channels.

To activate a manually-chosen channel or set of channels immediately and
once only, even at a time when such channel would not normally be
activated, add the `--execute-now` switch followed by any of `hourly`,
`8hourly`, `daily`, `weekly`, `monthly` and `test`.

The `test` channel will never be activated during normal usage. Note that
the user config setting for the `test` channel is hidden, and can be
selected by executing the following JavaScript while editing a user config
page:

```js
document.querySelector("[name=field-frequency]").value = "test"
```

To restrict which wikis posts will be downloaded from, add `--limit-wikis
[list]`.

## Remote deployment

The notifier service is not intended to be executed locally or even to be
executed as a continuously-running service during production, but rather to
be deployed to the cloud using AWS Lambda and a handler that calls
`--execute-now`.

See [docs/deployment.md](/docs/deployment.md) for more information and instructions.

# Development

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

## Testing

### Testing locally

To run tests directly on your machine:

```shell
poetry run pytest --notifier-config path_to_config_file --notifier-auth path_to_auth_file
```

"_test" will be appended to whatever database name is configured, as
described above. Database tests (`tests/test_database.py`) require that
this database already exist.

I recommend using a MySQL server on localhost for tests.

### Testing with Docker

A Docker Compose setup is present that will spin up a temporary MySQL database
and run tests against it:

```shell
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Status

Status frontends are located at:

* https://croque-scp.github.io/notifier/status.html
* https://croque-scp.github.io/notifier/graphs.html
