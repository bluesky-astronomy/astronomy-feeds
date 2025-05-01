BEGIN TRANSACTION;
DROP TABLE IF EXISTS "account";
CREATE TABLE "account" (
  "id" SERIAL PRIMARY KEY
,  "handle" varchar(255) NOT NULL
,  "submission_id" varchar(255) NOT NULL
,  "did" varchar(255) NOT NULL
,  "is_valid" boolean NOT NULL
,  "feed_all" boolean NOT NULL
,  "indexed_at" timestamp NOT NULL
,  "mod_level" integer NOT NULL
,  "is_muted" boolean NOT NULL
,  "is_banned" boolean NOT NULL
,  "hidden_count" integer NOT NULL
,  "muted_count" integer NOT NULL
,  "banned_count" integer NOT NULL
,  "warned_count" integer NOT NULL
);
DROP INDEX IF EXISTS "account_did";
CREATE INDEX "account_did" ON "account" ("did");
DROP INDEX IF EXISTS "account_handle";
CREATE INDEX "account_handle" ON "account" ("handle");
DROP INDEX IF EXISTS "account_indexed_at";
CREATE INDEX "account_indexed_at" ON "account" ("indexed_at");
DROP INDEX IF EXISTS "account_is_banned";
CREATE INDEX "account_is_banned" ON "account" ("is_banned");
DROP INDEX IF EXISTS "account_is_muted";
CREATE INDEX "account_is_muted" ON "account" ("is_muted");
DROP INDEX IF EXISTS "account_is_valid";
CREATE INDEX "account_is_valid" ON "account" ("is_valid");
DROP INDEX IF EXISTS "account_mod_level";
CREATE INDEX "account_mod_level" ON "account" ("mod_level");
DROP INDEX IF EXISTS "idx_account_account_did_is_valid";
CREATE INDEX "idx_account_account_did_is_valid" ON "account" ("did","is_valid");
DROP INDEX IF EXISTS "idx_account_account_handle";
CREATE INDEX "idx_account_account_handle" ON "account" ("handle");
DROP INDEX IF EXISTS "idx_account_account_is_banned";
CREATE INDEX "idx_account_account_is_banned" ON "account" ("is_banned");
DROP INDEX IF EXISTS "idx_account_account_is_muted";
CREATE INDEX "idx_account_account_is_muted" ON "account" ("is_muted");
DROP INDEX IF EXISTS "idx_account_account_is_valid";
CREATE INDEX "idx_account_account_is_valid" ON "account" ("is_valid");
DROP INDEX IF EXISTS "idx_account_account_mod_level";
CREATE INDEX "idx_account_account_mod_level" ON "account" ("mod_level");
COMMIT;
