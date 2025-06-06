/* this script updates foreign schema in the dev database when prod 
schema changes (**WILL** delete current data in developer database) */

BEGIN TRANSACTION;

-- reimport remote schema
DROP SCHEMA IF EXISTS prod_public CASCADE;
CREATE SCHEMA prod_public;
IMPORT FOREIGN SCHEMA public FROM SERVER prod_server INTO prod_public;

-- recreate local schema (assuming there is a schema dump from prod in 'schema.sql')
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
\i schema.sql

COMMIT;