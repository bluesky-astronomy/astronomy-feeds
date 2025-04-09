Scripts to generate the SQL tables necessary for the Bluesky Astrofeed service.

Simply execute bootstrap.sql, which will call each individual table's create script to create the DB schema.

dump_data.sql can be executed on an existing database to generate SQL INSERT statements useful for migrating from one
environment to another.

You will have to manually insert a row into SubscriptionState to set the cursor value from ATPROTO
    INSERT INTO "subscriptionstate" ("id","service","cursor") VALUES (1,'did:web:feed-all.astronomy.blue',7260730000);

After migrating data into the new structure, be sure to execute 'update_sequences.sql' to ensure the sequences are set
properly, or duplicate key errors will occur upon insert.