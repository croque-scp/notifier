# Authentication

In addition to the config file based on the one provided in this
repository, notifier requires an additional authentication file to provide
passwords etc. for the various services it requires.

## File format

The authentication file should take the following form, as a TOML document:

```toml
wikidot_password = "<Wikidot password for username in config file>"
gmail_password = "<Gmail password for username in config file>"
mysql_host = "<IP of MySQL server>"
mysql_username = "<username for MySQL connection>"
mysql_password = "<password for MySQL connection>"
```

Use these keys directly if you wish to pass the authentication secrets via
this file directly. In this case it is imperative that this file is never
made public (e.g. make sure to add it to your .gitignore).

A version of this file with dummy values used for CI testing can be found
at [config/auth.ci.toml](/config/auth.ci.toml).

## External values

The authentication file can also specify for the retrieval of keys from
other sources, by appending the following:

```toml
[[external]]
source = "<source name>"
<any extra keys required for to access source>
use_keys = [
  ["<key name in external source>", "<local key name>"],
  ...
]
```

The `source` item specifies the source to use. The `use_keys` item maps key
found in the external source to local keys, specified above. After all
external secrets have been retrieved, all of the required local values are
expected to be present.

At the time of writing the only supported external source is
[AWS Secrets Manager](https://aws.amazon.com/secrets-manager/), which
requires the following extra keys:

```toml
source = "AWSSecretsManager"
region_name = "<AWS region>"
secret_name = "<AWS secret name>"
```

See [config/auth.lambda.toml](/config/auth.lambda.toml) for a sample.