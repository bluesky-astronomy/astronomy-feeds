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

-- not taking SubscriptionState, ActivityLog, or NormalizedFeedStats for now