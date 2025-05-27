/* run this to connect a newly created (and ideally empty) dev database
to the prod database (only needs to be done once) */

-- variables that will be used for the setup, under the following assumptions
--    * we can access the server as superuser 'postgres', with a password 
--      defined in environment variable PGPASSWORD
--    * the prod and dev databases are on the same local server, at port 5432
\set dev_db_name   devdb
\set prod_db_name  proddb
\set prod_user     postgres
\set prod_password `echo $PGPASSWORD`
\set prod_host     localhost
\set prod_port     5432

-- if there is an existing dev database, drop it; create a new dev database, then connect to it
DROP DATABASE IF EXISTS :dev_db_name;
CREATE DATABASE :dev_db_name;
\connect :dev_db_name

-- assuming we have the FDW extension
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- now we have to make the server
CREATE SERVER IF NOT EXISTS prod_server 
FOREIGN DATA WRAPPER postgres_fdw 
OPTIONS (host :'prod_host', dbname :'prod_db_name', port :'prod_port');

-- make a user mapping to a remote user with the access we need; the local user either needs to be required to 
-- provide a password to log in locally, or needs to be a super user locally
CREATE USER MAPPING IF NOT EXISTS FOR current_user
SERVER prod_server 
OPTIONS (user :'prod_user', password :'prod_password');