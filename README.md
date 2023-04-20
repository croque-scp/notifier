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

In addition to the config file based on the one provided in this
repository, notifier requires an additional authentication file to provide
passwords etc. for the various services it requires.

See [docs/auth.md](/docs/auth.md) for more information and instructions.

## Database setup

For local development and testing, notifier requires a database to be set
up on a version of MySQL that is compatible with Amazon Aurora Serverless
v1.

See [docs/database.md](/docs/database.md) for more information and
instructions.

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

To run tests locally:

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