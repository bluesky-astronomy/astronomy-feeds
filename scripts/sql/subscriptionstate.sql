BEGIN TRANSACTION;
DROP TABLE IF EXISTS "subscriptionstate";
CREATE TABLE "subscriptionstate" (
  "id" SERIAL PRIMARY KEY
,  "service" varchar(255) NOT NULL
,  "cursor" BIGINT NOT NULL
,  UNIQUE ("service")
);

DROP INDEX IF EXISTS "subscriptionstate_service";
CREATE UNIQUE INDEX "subscriptionstate_service" ON "subscriptionstate" ("service");
COMMIT;
