BEGIN TRANSACTION;
DROP TABLE IF EXISTS "activitylog";
CREATE TABLE "activitylog" (
  "id" SERIAL PRIMARY KEY 
,  "request_dt" timestamp NOT NULL
,  "request_feed_uri" varchar(255) NOT NULL
,  "request_limit" integer NOT NULL
,  "request_is_scrolled" boolean NOT NULL DEFAULT FALSE
,  "request_user_did" varchar(255) DEFAULT NULL
);
DROP INDEX IF EXISTS "activitylog_request_dt";
CREATE INDEX "activitylog_request_dt" ON "activitylog" ("request_dt");
DROP INDEX IF EXISTS "activitylog_request_feed_uri";
CREATE INDEX "activitylog_request_feed_uri" ON "activitylog" ("request_feed_uri");
DROP INDEX IF EXISTS "activitylog_request_user_did";
CREATE INDEX "activitylog_request_user_did" ON "activitylog" ("request_user_did");
DROP INDEX IF EXISTS "idx_activitylog_request_dt_index";
CREATE INDEX "idx_activitylog_request_dt_index" ON "activitylog" ("request_dt");
DROP INDEX IF EXISTS "idx_activitylog_request_feed_uri_index";
CREATE INDEX "idx_activitylog_request_feed_uri_index" ON "activitylog" ("request_feed_uri");
DROP INDEX IF EXISTS "idx_activitylog_request_user_did_index";
CREATE INDEX "idx_activitylog_request_user_did_index" ON "activitylog" ("request_user_did");
COMMIT;
