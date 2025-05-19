/* run this to connect a newly created (and ideally empty) dev database
to the prod database (only needs to be done once) */

-- variables that will be used for the setup
\set dev_db_name   astrosky_astronomy_dev   -- based on current naming convention
\set prod_db_name  astrosky_astronomy
\set prod_user     postgres                 -- assuming we are superuser 'postgres'
\set prod_password `echo $PGPASSWORD`       -- take this from env so we don't hard code a password
\set prod_host     localhost                -- assuming prod is on the same server, with standard config
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