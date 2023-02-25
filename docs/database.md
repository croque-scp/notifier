# Database setup

notifier uses MySQL. It and the database need to be set up before it can
operate, or before tests can be run.

This document assumes some familiarity with
[Docker](https://www.docker.com/).

## Setting up MySQL

notifier is designed to use [Amazon Aurora Serverless
v1](https://aws.amazon.com/rds/aurora/serverless/) during production. The
latest version of MySQL supported by Aurora Serverless is 5.6.10 (for
reference, the latest version of MySQL at the time of writing is 8.0.26).
For this reason, a compatible version of MySQL is needed for local
development.

(Note 2023-02-25: The database has been upgraded to MySQL 5.7 as part of a
mandatory Aurora engine upgrade.)

[Docker](https://www.docker.com/) is used for pinning the MySQL version,
and to avoid this version conflicting with any MySQL already installed on
your system.

The earliest version of MySQL 5.6 available in the official MySQL Docker
registry is 5.6.17; therefore, although it's not ideal, I recommend running
tests locally against this version of MySQL. This is also the version that
[I use in CI](/.github/workflows/tests.yml).

Create the MySQL Server container:

```shell
docker create --name notifier_mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  mysql:5.6.17
```

For an ephemeral, development-only, containerised MySQL installation I'm
cool with just setting the root password insecurely like this. Obviously
don't do this in production.

Start the container:

```shell
docker start notifier_mysql
```

To access the database using the MySQL client:

```shell
mysql -h127.0.0.1 -uroot -proot
```

If `127.0.0.1` doesn't work you may need to find the IP of the Docker
container and use that instead:

```shell
docker inspect \
  -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
  notifier_mysql
```

Once inside the database server, you can create the database.

## Creating the database

A new user will need to be created for the notifier, replacing the
placeholders with the MySQL-specific credentials supplied [during
authentication](/docs/auth.md):

```sql
CREATE USER '<username>'@'<host>' IDENTIFIED BY '<password>';
```

Create the database, with the database's name matching the name in the
config file (default: `wikidot_notifier`), and grant the new user access to
it:

```sql
CREATE DATABASE `<name>` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
GRANT ALL PRIVILEGES ON `<name>`.* TO '<username>'@'<host>';
```

In order to run tests, a test database will also need to be created. The
name of this database is the same as the configured name, with "_test"
appended:

```sql
CREATE DATABASE `<name>_test` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
GRANT ALL PRIVILEGES ON `<name>_test`.* TO '<username>'@'<host>';
```