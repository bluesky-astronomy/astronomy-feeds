/* run this to connect a newly created (and ideally empty) dev database
to the prod database (only needs to be done once) */

-- if there is an existing dev database, drop it; create a new dev database, then connect to it
DROP DATABASE IF EXISTS astrosky_astronomy_dev;
CREATE DATABASE astrosky_astronomy_dev;
\connect astrosky_astronomy_dev

-- assuming we have the FDW extension
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- now we have to make the server; assuming we're on the same machine as prod, not sure if dbname is needed here?
CREATE SERVER IF NOT EXISTS prod_server 
FOREIGN DATA WRAPPER postgres_fdw 
OPTIONS (host 'localhost', dbname 'astrosky_astronomy', port '5432');

-- make a user mapping to a remote user with the access we need; the local user either needs to be required to 
-- provide a password to log in locally, or needs to be a super user locally
CREATE USER MAPPING IF NOT EXISTS FOR postgres
SERVER prod_server 
OPTIONS (user 'postgres', password 'secret');