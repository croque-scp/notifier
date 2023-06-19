# Database setup

notifier uses MySQL. It and the database need to be set up before it can
operate, or before tests can be run.

notifier uses the latest stable release of MySQL as of the time of writing, 8.0.33.

Running in the cloud, Docker is no longer needed and introduces an unnecessary performance overhead for production. Spin up a dedicated server of some kind and install MySQL directly onto it.

## Setting up MySQL

### Locally

Running on your local machine, I advise running MySQL in a [Docker](https://www.docker.com/) container. This is to avoid this version conflicting with any MySQL already installed on your system, and to make it easy to pin a required version.

Create the MySQL Server container:

```shell
docker create --name notifier_mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root mysql:8.0.33
```

For an ephemeral, development-only, containerised MySQL installation I'm
cool with just setting the root password insecurely like this. Obviously
don't do this in production.

Start the container:

```shell
docker start notifier_mysql
```

To access the database from the local command line using the MySQL client, use `127.0.0.1` the local loopback interface (`localhost` doesn't work in my experience):

```shell
mysql -h127.0.0.1 -uroot -proot
```

If `127.0.0.1` doesn't work you may need to find the IP of the Docker
container and use that instead:

```shell
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' notifier_mysql
```

Once inside the database server, you can create the database.

If you want to connect to the database from inside a _different_ Docker container (e.g. a container running the main notifier Python application), '`127.0.0.1`' pinged from inside that container will refer to itself, not to the database container. You will need to connect the two containers via a Docker network. There are plenty of methods of doing that but the easiest in my opinion is adding a `--network` flag to the command used to launch the 2nd container, instructing it to use the database's network stack:

```shell
docker run --network=container:notifier_mysql ...
```


### In the cloud

Left as an exercise for the reader.

I recommend installing from source if possible to get the latest version.

If deploying the database as an AWS EC2 on a private VPS, you can cheat and get internet connectivity to download the necessary files by temporarily assigning it an Elastic IP. Just remember to dissociate _and release_ it afterwards.

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