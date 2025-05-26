/* run this to refresh the dev database data (either to ingest 
new data from prod, or to change how it is sampled) */

-- Post; take 50k for now
DROP TABLE IF EXISTS public.post;
CREATE TABLE public.post (
    like prod_public.post including all
);
INSERT INTO public.post
SELECT * from prod_public.post
LIMIT 50000;

-- ModActions; take all for now
DROP TABLE IF EXISTS public.modactions;
CREATE TABLE public.modactions (
    like prod_public.modactions including all
);
INSERT INTO public.modactions
SELECT * from prod_public.modactions;

-- BotActions; take all for now
DROP TABLE IF EXISTS public.botactions;
CREATE TABLE public.botactions (
    like prod_public.botactions including all
);
INSERT INTO public.botactions
SELECT * from prod_public.botactions;

-- Account; take all for now
DROP TABLE IF EXISTS public.account;
CREATE TABLE public.account (
    like prod_public.account including all
);
INSERT INTO public.account
SELECT * from prod_public.account;

-- SubscriptionState; take all for now
DROP TABLE IF EXISTS public.subscriptionstate;
CREATE TABLE public.subscriptionstate (
    like prod_public.subscriptionstate including all
);
INSERT INTO public.subscriptionstate
SELECT * from prod_public.subscriptionstate;

-- ActivityLog; take all times Emily has viewed the feeds for now...
-- TODO: replace with anonymizing the DID of users viewing the feed
DROP TABLE IF EXISTS public.activitylog;
CREATE TABLE public.activitylog (
    like prod_public.activitylog including all
);
INSERT INTO public.activitylog
SELECT * from prod_public.activitylog WHERE prod_public.activitylog.request_user_did = 'did:plc:jcoy7v3a2t4rcfdh6i4kza25' LIMIT 1000;

-- not taking NormalizedFeedStats for now - maybe generate on the fly?