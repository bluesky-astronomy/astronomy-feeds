BEGIN TRANSACTION;
DROP TABLE IF EXISTS "post";
CREATE TABLE "post" (
  "id" SERIAL PRIMARY KEY
,  "uri" varchar(255) NOT NULL
,  "cid" varchar(255) NOT NULL
,  "author" varchar(255) NOT NULL
,  "text" varchar(500) NOT NULL
,  "feed_all" boolean NOT NULL DEFAULT FALSE
,  "feed_astro" boolean NOT NULL DEFAULT FALSE
,  "indexed_at" timestamp NOT NULL
,  "feed_exoplanets" boolean NOT NULL DEFAULT FALSE
,  "feed_astrophotos" boolean NOT NULL DEFAULT FALSE
,  "feed_cosmology" boolean NOT NULL DEFAULT FALSE
,  "feed_extragalactic" boolean NOT NULL DEFAULT FALSE
,  "feed_highenergy" boolean NOT NULL DEFAULT FALSE
,  "feed_instrumentation" boolean NOT NULL DEFAULT FALSE
,  "feed_methods" boolean NOT NULL DEFAULT FALSE
,  "feed_milkyway" boolean NOT NULL DEFAULT FALSE
,  "feed_planetary" boolean NOT NULL DEFAULT FALSE
,  "feed_radio" boolean NOT NULL DEFAULT FALSE
,  "feed_stellar" boolean NOT NULL DEFAULT FALSE
,  "feed_education" boolean NOT NULL DEFAULT FALSE
,  "feed_history" boolean NOT NULL DEFAULT FALSE
,  "hidden" boolean NOT NULL DEFAULT FALSE
,  "likes" integer NOT NULL DEFAULT '0'
,  "feed_research" boolean NOT NULL DEFAULT FALSE
,  "feed_solar" boolean NOT NULL DEFAULT FALSE
,  "feed_questions" boolean NOT NULL DEFAULT FALSE
);
DROP INDEX IF EXISTS "idx_post_cid";
CREATE INDEX "idx_post_cid" ON "post" ("cid");
DROP INDEX IF EXISTS "idx_post_feed_questions";
CREATE INDEX "idx_post_feed_questions" ON "post" ("feed_questions");
DROP INDEX IF EXISTS "idx_post_feed_research";
CREATE INDEX "idx_post_feed_research" ON "post" ("feed_research");
DROP INDEX IF EXISTS "idx_post_feed_solar";
CREATE INDEX "idx_post_feed_solar" ON "post" ("feed_solar");
DROP INDEX IF EXISTS "idx_post_post_author";
CREATE INDEX "idx_post_post_author" ON "post" ("author");
DROP INDEX IF EXISTS "idx_post_post_feed_all";
CREATE INDEX "idx_post_post_feed_all" ON "post" ("feed_all");
DROP INDEX IF EXISTS "idx_post_post_feed_astro";
CREATE INDEX "idx_post_post_feed_astro" ON "post" ("feed_astro");
DROP INDEX IF EXISTS "idx_post_post_feed_astrophotos";
CREATE INDEX "idx_post_post_feed_astrophotos" ON "post" ("feed_astrophotos");
DROP INDEX IF EXISTS "idx_post_post_feed_cosmology";
CREATE INDEX "idx_post_post_feed_cosmology" ON "post" ("feed_cosmology");
DROP INDEX IF EXISTS "idx_post_post_feed_education";
CREATE INDEX "idx_post_post_feed_education" ON "post" ("feed_education");
DROP INDEX IF EXISTS "idx_post_post_feed_exoplanets";
CREATE INDEX "idx_post_post_feed_exoplanets" ON "post" ("feed_exoplanets");
DROP INDEX IF EXISTS "idx_post_post_feed_extragalactic";
CREATE INDEX "idx_post_post_feed_extragalactic" ON "post" ("feed_extragalactic");
DROP INDEX IF EXISTS "idx_post_post_feed_highenergy";
CREATE INDEX "idx_post_post_feed_highenergy" ON "post" ("feed_highenergy");
DROP INDEX IF EXISTS "idx_post_post_feed_history";
CREATE INDEX "idx_post_post_feed_history" ON "post" ("feed_history");
DROP INDEX IF EXISTS "idx_post_post_feed_instrumentation";
CREATE INDEX "idx_post_post_feed_instrumentation" ON "post" ("feed_instrumentation");
DROP INDEX IF EXISTS "idx_post_post_feed_methods";
CREATE INDEX "idx_post_post_feed_methods" ON "post" ("feed_methods");
DROP INDEX IF EXISTS "idx_post_post_feed_milkyway";
CREATE INDEX "idx_post_post_feed_milkyway" ON "post" ("feed_milkyway");
DROP INDEX IF EXISTS "idx_post_post_feed_planetary";
CREATE INDEX "idx_post_post_feed_planetary" ON "post" ("feed_planetary");
DROP INDEX IF EXISTS "idx_post_post_feed_radio";
CREATE INDEX "idx_post_post_feed_radio" ON "post" ("feed_radio");
DROP INDEX IF EXISTS "idx_post_post_feed_stellar";
CREATE INDEX "idx_post_post_feed_stellar" ON "post" ("feed_stellar");
DROP INDEX IF EXISTS "idx_post_post_hidden";
CREATE INDEX "idx_post_post_hidden" ON "post" ("hidden");
DROP INDEX IF EXISTS "idx_post_post_indexed_at";
CREATE INDEX "idx_post_post_indexed_at" ON "post" ("indexed_at");
DROP INDEX IF EXISTS "idx_post_post_uri";
CREATE INDEX "idx_post_post_uri" ON "post" ("uri");
COMMIT;
