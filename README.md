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

To start the notifier service locally:

```shell
poetry run python3 -m notifier path_to_config_file path_to_auth_file
```

The config file that my notifier instance uses is `config.toml`. A sample
auth file with dummy secrets, used for CI tests, can be found at
`.github/auth.ci.toml`.

The service will run continuously and activate an automatically-determined
set of notification channels each hour.

To activate a channel or multiple channels immediately and once only, add
the `--execute-now` switch followed by any of `hourly`, `daily`, `weekly`
and `monthly`.

To activate an automatically-determined set of channels immediately and
once only, add the `--execute-now` switch with no parameter. Note that this
must be run during the first minute of an hour to match any channels.

## Remote deployment

The notifier service is not intended to be executed locally, but to be
deployed to the cloud using AWS Lambda.

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

Run tests:

```shell
poetry run pytest --notifier-config path_to_config_file --notifier-auth path_to_auth_file
```

"_test" will be appended to whatever database name is configured, as
described above. Database tests (`tests/test_database.py`) require that
this database already exist.

I recommend using a MySQL server on localhost for tests.
