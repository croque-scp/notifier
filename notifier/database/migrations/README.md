# Migrations

This directory is for migrations.

Migrations have the following name format:

```
<3 digit number>-<name>.up.sql
```

The number corresponds to the effective migration version after applying
the migration.

## Adding a new migration

New migrations must be added in sequential order, with no missed migration
versions.

Migrations are not responsible for updating the database's migration
version.
