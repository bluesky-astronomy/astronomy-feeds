BEGIN TRANSACTION;
DROP TABLE IF EXISTS "botactions";
CREATE TABLE "botactions" (
  "id" SERIAL PRIMARY KEY
,  "indexed_at" timestamp NOT NULL
,  "did" varchar(255) NOT NULL
,  "type" varchar(255) NOT NULL
,  "stage" varchar(255) NOT NULL
,  "parent_uri" varchar(255) NOT NULL
,  "parent_cid" varchar(255) NOT NULL
,  "latest_uri" varchar(255) NOT NULL
,  "latest_cid" varchar(255) NOT NULL
,  "complete" integer NOT NULL
,  "authorized" integer NOT NULL
,  "checked_at" timestamp NOT NULL
);
DROP INDEX IF EXISTS "botactions_authorized";
CREATE INDEX "botactions_authorized" ON "botactions" ("authorized");
DROP INDEX IF EXISTS "botactions_checked_at";
CREATE INDEX "botactions_checked_at" ON "botactions" ("checked_at");
DROP INDEX IF EXISTS "botactions_complete";
CREATE INDEX "botactions_complete" ON "botactions" ("complete");
DROP INDEX IF EXISTS "botactions_indexed_at";
CREATE INDEX "botactions_indexed_at" ON "botactions" ("indexed_at");
DROP INDEX IF EXISTS "botactions_stage";
CREATE INDEX "botactions_stage" ON "botactions" ("stage");
DROP INDEX IF EXISTS "botactions_type";
CREATE INDEX "botactions_type" ON "botactions" ("type");
DROP INDEX IF EXISTS "idx_botactions_botactions_authorized";
CREATE INDEX "idx_botactions_botactions_authorized" ON "botactions" ("authorized");
DROP INDEX IF EXISTS "idx_botactions_botactions_checked_at";
CREATE INDEX "idx_botactions_botactions_checked_at" ON "botactions" ("checked_at");
DROP INDEX IF EXISTS "idx_botactions_botactions_complete";
CREATE INDEX "idx_botactions_botactions_complete" ON "botactions" ("complete");
DROP INDEX IF EXISTS "idx_botactions_botactions_indexed_at";
CREATE INDEX "idx_botactions_botactions_indexed_at" ON "botactions" ("indexed_at");
DROP INDEX IF EXISTS "idx_botactions_botactions_stage";
CREATE INDEX "idx_botactions_botactions_stage" ON "botactions" ("stage");
DROP INDEX IF EXISTS "idx_botactions_botactions_type";
CREATE INDEX "idx_botactions_botactions_type" ON "botactions" ("type");
COMMIT;
