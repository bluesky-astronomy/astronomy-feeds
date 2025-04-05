drop materialized view if exists normalizedfeedstats;

create materialized view normalizedfeedstats as
select id, request_feed_uri, extract(isoyear from request_dt) as year
, extract(month from request_dt) as month
, extract(day from request_dt) as day
, extract(hour from request_dt) as hour
, extract(dow from request_dt) as day_of_week
from activitylog
with data;

CREATE UNIQUE INDEX idx_normalized_feed_stats_id
ON normalizedfeedstats (id);
DROP INDEX IF EXISTS normalizedfeedstats_day;
CREATE INDEX normalizedfeedstats_day ON normalizedfeedstats (day);
DROP INDEX IF EXISTS normalizedfeedstats_day_of_week;
CREATE INDEX normalizedfeedstats_day_of_week ON normalizedfeedstats (day_of_week);
DROP INDEX IF EXISTS normalizedfeedstats_hour;
CREATE INDEX normalizedfeedstats_hour ON normalizedfeedstats (hour);
DROP INDEX IF EXISTS normalizedfeedstats_month;
CREATE INDEX normalizedfeedstats_month ON normalizedfeedstats (month);
DROP INDEX IF EXISTS normalizedfeedstats_request_feed_uri;
CREATE INDEX normalizedfeedstats_request_feed_uri ON normalizedfeedstats (request_feed_uri);
DROP INDEX IF EXISTS normalizedfeedstats_year;
CREATE INDEX normalizedfeedstats_year ON normalizedfeedstats (year);