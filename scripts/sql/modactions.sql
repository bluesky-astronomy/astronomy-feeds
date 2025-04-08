BEGIN TRANSACTION;
DROP TABLE IF EXISTS "modactions";
CREATE TABLE "modactions" (
  "id" SERIAL PRIMARY KEY
,  "indexed_at" timestamp NOT NULL
,  "did_mod" varchar(255) NOT NULL
,  "did_user" varchar(255) NOT NULL
,  "action" varchar(255) NOT NULL
,  "expiry" timestamp DEFAULT NULL
);
DROP INDEX IF EXISTS "idx_modactions_modactions_action";
CREATE INDEX "idx_modactions_modactions_action" ON "modactions" ("action");
DROP INDEX IF EXISTS "idx_modactions_modactions_did_mod";
CREATE INDEX "idx_modactions_modactions_did_mod" ON "modactions" ("did_mod");
DROP INDEX IF EXISTS "idx_modactions_modactions_did_user";
CREATE INDEX "idx_modactions_modactions_did_user" ON "modactions" ("did_user");
DROP INDEX IF EXISTS "idx_modactions_modactions_expiry";
CREATE INDEX "idx_modactions_modactions_expiry" ON "modactions" ("expiry");
DROP INDEX IF EXISTS "idx_modactions_modactions_indexed_at";
CREATE INDEX "idx_modactions_modactions_indexed_at" ON "modactions" ("indexed_at");
DROP INDEX IF EXISTS "modactions_action";
CREATE INDEX "modactions_action" ON "modactions" ("action");
DROP INDEX IF EXISTS "modactions_did_mod";
CREATE INDEX "modactions_did_mod" ON "modactions" ("did_mod");
DROP INDEX IF EXISTS "modactions_did_user";
CREATE INDEX "modactions_did_user" ON "modactions" ("did_user");
DROP INDEX IF EXISTS "modactions_expiry";
CREATE INDEX "modactions_expiry" ON "modactions" ("expiry");
DROP INDEX IF EXISTS "modactions_indexed_at";
CREATE INDEX "modactions_indexed_at" ON "modactions" ("indexed_at");
COMMIT;
