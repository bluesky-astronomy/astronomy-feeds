/* this script (re-)creates a developer database from scratch (dropping an existing one
if it exists), and connects it to a production database via FDW */

-- variables that will be used for the setup, under the following assumptions
--    * we can access the server as superuser 'postgres'
--    * there is a database called 'proddb' on the server
-- (note: because we will create devdb on the same server as proddb, and the host and 
-- port are only needed for mapping from devdb to proddb, we simply use 'localhost' 
-- and whatever port our proddb connection uses as the mapping connection parameters)
\set dev_db_name   devdb
\set prod_db_name  proddb
\set prod_user     postgres
\set prod_host     localhost
SELECT inet_server_port() as prod_port \gset

-- if there is an existing dev database, drop it; create a new dev database, then connect to it
\connect :prod_db_name
DROP DATABASE IF EXISTS :dev_db_name;
CREATE DATABASE :dev_db_name;
\connect :dev_db_name

BEGIN TRANSACTION;

-- install our FDW extension on a dedicated schema that won't be dropped during prod schema updates
CREATE SCHEMA fdw_setup;
CREATE EXTENSION postgres_fdw SCHEMA fdw_setup;

-- now we have to make the server using our pre-set connection parameters
CREATE SERVER prod_server 
FOREIGN DATA WRAPPER postgres_fdw 
OPTIONS (host :'prod_host', dbname :'prod_db_name', port :'prod_port');

-- make a user mapping to specified user on the remote server (current and remote user must be superuser
-- on respective servers to do this passwordless; currently the foreign server is the same server as the 
-- remote server, and current_user should be the same superuser as prod_user)
CREATE USER MAPPING FOR current_user
SERVER prod_server
OPTIONS (user :'prod_user');

COMMIT;