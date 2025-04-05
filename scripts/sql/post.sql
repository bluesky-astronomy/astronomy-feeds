BEGIN TRANSACTION;
DROP TABLE IF EXISTS "post";
CREATE TABLE "post" (
  "id" SERIAL PRIMARY KEY
,  "uri" varchar(255) NOT NULL
,  "cid" varchar(255) NOT NULL
,  "author" varchar(255) NOT NULL
,  "text" varchar(500) NOT NULL
,  "feed_all" integer NOT NULL DEFAULT '0'
,  "feed_astro" integer NOT NULL DEFAULT '0'
,  "indexed_at" timestamp NOT NULL
,  "feed_exoplanets" integer NOT NULL DEFAULT '0'
,  "feed_astrophotos" integer NOT NULL DEFAULT '0'
,  "feed_cosmology" integer NOT NULL
,  "feed_extragalactic" integer NOT NULL
,  "feed_highenergy" integer NOT NULL
,  "feed_instrumentation" integer NOT NULL
,  "feed_methods" integer NOT NULL
,  "feed_milkyway" integer NOT NULL
,  "feed_planetary" integer NOT NULL
,  "feed_radio" integer NOT NULL
,  "feed_stellar" integer NOT NULL
,  "feed_education" integer NOT NULL
,  "feed_history" integer NOT NULL
,  "hidden" integer NOT NULL
,  "likes" integer NOT NULL
,  "feed_research" integer NOT NULL
,  "feed_solar" integer NOT NULL
,  "feed_questions" integer NOT NULL
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
