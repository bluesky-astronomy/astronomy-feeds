/* run this to update foreign schema in the dev database when prod 
schema changes (NOT needed to retrieve new data in unchanged schema) */

-- reimport remote schema
DROP SCHEMA IF EXISTS prod_public CASCADE;
CREATE SCHEMA prod_public;
IMPORT FOREIGN SCHEMA public FROM SERVER prod_server INTO prod_public;