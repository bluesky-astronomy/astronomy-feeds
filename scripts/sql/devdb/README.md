This directory contains machinery for creating a developer database (and associated dump file that can be distributed to developers to recreate that database), given access to a production database.

### Motivation

The source code is organized as follows: there are several actions that a user might wish to perform, related to the creation and maintenance of such a database; and these actions will each involve series of processes being carried out on the database(s) themselves; and there is significant overlap in the database process steps required for each user action. So, to make things smoother for users and to avoid code duplication, we have organized this source code into two "layers": the database process layer, implemented in SQL script files that each perform an isoltated database process; and the user action layer, in which those database processes are bundled together in the correct order to produce an anticipated user action.

The database process layer consists of the following processes (implemented in the specified SQL script files):
1. create a developer database, and connect it to the production database via FDW ([setup_dev_db.sql](scripts/sql/dev_db/setup_dev_db.sql))
2. set up schemas in the developer database that reflect the production database schema; both by importing the production schema as a foreign schema via the FDW connection, and by recreating the production schema locally via a `pg_dump` SQL script ([update_dev_db.sql](scripts/sql/dev_db/update_dev_db.sql))
3. populate local tables in the developer database with production data, by sampling and moving data from FDW wrapped production tables to their local equivalents ([populate_dev_db.sql](scripts/sql/dev_db/populate_dev_db.sql))

And the user action layer consists of the following actions (requiring the specified database processes; and implemented in the specified executable bash scripts):
* create a developer database from scratch (database processes 1, 2, and 3; [build_dev_db](scripts/sql/dev_db/build_dev_db))
* update the developer database schema and data, to reflect a change in the production database schema (database processes 2 and 3; [update_dev_db_schema](scripts/sql/dev_db/update_dev_db_schema))
* repopulate the developer database with fresh data from the production database, without a schema change (database process 3; [update_dev_db_data](scripts/sql/dev_db/update_dev_db_data))

### Usage

Use of this code should be accomplished by executing the bash script that corresponds to the desired action:
* [build_dev_db](scripts/sql/dev_db/build_dev_db): Creates a developer database from scratch. Run this one time, at the beginning of setting up the developer database; or any time you wish to recreate the developer database (**WARNING**: this will **delete the existing developer database** if there is one)
* [update_dev_db_schema](scripts/sql/dev_db/update_dev_db_schema): Updates the file `schema.sql` with a dump of the current schema from the production database; (re-)imports the production database schema as a foreign schema in the developer database, and uses updated schema dump file to (re-)create the same schema locally in the developer database. Run this any time the production database schema has changed, to update the developer database to use the new schema, and update its data (**WARNING**: this will **replace existing developer database data** with data sampled from the production database at the time of running)
* [update_dev_db_data](scripts/sql/dev_db/update_dev_db_data): (Re-)populates the local developer database tables with data from the production database, via the FDW wrapped foreign tables, according to whatever sampling logic is defined in [populate_dev_db.sql](scripts/sql/dev_db/populate_dev_db.sql). Run this whenever you wish to refresh the developer database with up-to-date data from the production database, or to re-sample data from the production database according to a new sampling strategy (**WARNING**: while the sampling logic may change over time, **at time of writing this will replace existing developer database data**, and is very likely to continue to do so)

### Requirements

In order for these scripts to work correctly, they must be executed in an environment with access to a PostgreSQL server with a database named `proddb` (for [build_dev_db](scripts/sql/dev_db/build_dev_db)) _and_ a database named `devdb` (for [update_dev_db_schema](scripts/sql/dev_db/update_dev_db_schema) and [update_dev_db_data](scripts/sql/dev_db/update_dev_db_data)), in which `proddb` contains all tables and other structures used by the sampling logic in [populate_dev_db.sql](scripts/sql/dev_db/populate_dev_db.sql), and which has a superuser called `postgres`. PostgreSQL client services `psql` and `pg_dump` must be installed and accessible.

In addition, certain connection parameters for the PostgreSQL server (host name, port number, and a password that will allow the `postgres` superuser to access the `proddb` and `devdb` databases) must be specified at the environment level. In the case of the host and port name, this can be done through environment variables `PGHOST` and `PGPORT`, which will likely need to be set to `localhost` and `5432`, respectively (and exported for use in scripts, e.g. by setting them with `export PGHOST=localhost`, etc); although both may be able to be ommitted/left unset, if the system defaults are suitable.

In the case of the password, there are two ways to set it:
1. having a file named `.pgpass` located in the `HOME` directory, with **NO WORLD OR GROUP PERMISSIONS** (run `chmod 0600 ~/.pgpass`), which has lines of the format

   >  `host:port:database:user:password`

    as detailed [here](https://www.postgresql.org/docs/current/libpq-pgpass.html). A database connection request will automatically take a password from the first line of this file that matches its connection parameters (including when the parameter is specified in `.pgpass` with a wildcard `*`, which will match anything). As long as whichever lines are there specify a password for the user `postgres` to access databases `proddb` and `devdb`, this will work here; so anything from the most specific case, e.g.

    >  `localhost:5432:proddb:postgres:[yourpassword]`  
    `localhost:5432:devdb:postgres:[yourpassword]`

    which specifies passwords _only_ for user `postgres` connecting to `proddb` or `devdb` through port `5432` of `localhost`; to the most general

   >  `*:*:*:*:[yourpassword]`

    which gives the same password to any user connecting to any database through any port at any host, would work.

2. having the environment variable `$PGPASSWORD`set.

Approach 1, while being more complicated, may be preferred, as it is both more secure and more flexible (since it allows for setting this password without interfering with any other PostgreSQL setup).

A final note: the scripts here explicitly use `-U postgres -d [prod/dev]db` to access the target databases as the `postgres` user, so the values of environment variables `PGUSER` and `PGDATABASE` (or values for the user and database connection parameters coming from any other source) will be ignored even if they are set.