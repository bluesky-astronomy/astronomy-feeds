select
"INSERT INTO account (id,handle,submission_id,did,is_valid,feed_all,indexed_at,mod_level,is_muted,is_banned,hidden_count,muted_count,banned_count,warned_count) VALUES ("
|| id || ",'"
|| handle|| "','"
|| submission_id || "','"
|| did || "',"
|| is_valid || ","
|| feed_all || ",'"
|| indexed_at|| "',"
|| mod_level || ","
|| is_muted || ","
|| is_banned || ","
|| hidden_count || ","
|| muted_count || ","
|| banned_count || ","
|| warned_count || ")"
from account;


select
"INSERT INTO botactions (id,indexed_at,did,type,stage,parent_uri,parent_cid,latest_uri,latest_cid,complete,authorized,checked_at) VALUES ("
|| id || ",'"
|| indexed_at || "','"
|| did || "','"
|| type || "','"
|| stage || ",'"
|| parent_uri || "','"
|| parent_cid || "','"
|| latest_uri || "','"
|| latest_cid || "',"
|| complete || ","
|| authorized || ",'"
|| checked_at ||"')"
from botactions;


select
"INSERT INTO modactions (id,indexed_at,did_mod,did_user,action,expiry) VALUES ("
|| id || ",'"
|| indexed_at || "','"
|| did_mod || "','"
|| did_user || "','"
|| action || "', NULL)"
from modactions;


select
"insert into post (uri,cid,author,text,feed_all,feed_astro,indexed_at,feed_exoplanets,feed_astrophotos,feed_cosmology,feed_extragalactic,feed_highenergy,feed_instrumentation,feed_methods,feed_milkyway,feed_planetary,feed_radio,feed_stellar,feed_education,feed_history,hidden,likes,feed_research,feed_solar,feed_questions) values ('"
|| uri || "','"
|| cid || "','"
|| author || "','"
|| text || "',"
|| feed_all || ","
|| feed_astro || ",'"
|| indexed_at || "',"
|| feed_exoplanets || ","
|| feed_astrophotos || ","
|| feed_cosmology || ","
|| feed_extragalactic || ","
|| feed_highenergy || ","
|| feed_instrumentation || ","
|| feed_methods || ","
|| feed_milkyway || ","
|| feed_planetary || ","
|| feed_radio || ","
|| feed_stellar || ","
|| feed_education || ","
|| feed_history || ","
|| hidden || ","
|| likes || ","
|| feed_research || ","
|| feed_solar || ","
|| feed_questions || ")"
from post;


select
"insert into activitylog(id,request_dt,request_feed_uri,request_limit,request_is_scrolled,request_user_did) VALUES ("
|| id ||  ",'"
|| request_dt || "','"
|| request_feed_uri || "',"
|| request_limit || ","
|| request_is_scrolled || ",'"
|| request_user_did || "')"
from activitylog;
