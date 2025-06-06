--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.5 (Ubuntu 17.5-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account; Type: TABLE; Schema: public; Owner: astrosky_astronomy
--

CREATE TABLE public.account (
    id integer NOT NULL,
    handle character varying(255) NOT NULL,
    submission_id character varying(255) NOT NULL,
    did character varying(255) NOT NULL,
    is_valid boolean DEFAULT false NOT NULL,
    feed_all boolean DEFAULT false NOT NULL,
    indexed_at timestamp without time zone NOT NULL,
    mod_level integer NOT NULL,
    is_muted boolean DEFAULT false NOT NULL,
    is_banned boolean DEFAULT false NOT NULL,
    hidden_count integer NOT NULL,
    muted_count integer NOT NULL,
    banned_count integer NOT NULL,
    warned_count integer NOT NULL
);


ALTER TABLE public.account OWNER TO astrosky_astronomy;

--
-- Name: account_id_seq; Type: SEQUENCE; Schema: public; Owner: astrosky_astronomy
--

CREATE SEQUENCE public.account_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.account_id_seq OWNER TO astrosky_astronomy;

--
-- Name: account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: astrosky_astronomy
--

ALTER SEQUENCE public.account_id_seq OWNED BY public.account.id;


--
-- Name: activitylog; Type: TABLE; Schema: public; Owner: astrosky_astronomy
--

CREATE TABLE public.activitylog (
    id integer NOT NULL,
    request_dt timestamp without time zone NOT NULL,
    request_feed_uri character varying(255) NOT NULL,
    request_limit integer NOT NULL,
    request_is_scrolled boolean DEFAULT false NOT NULL,
    request_user_did character varying(255) DEFAULT NULL::character varying
);


ALTER TABLE public.activitylog OWNER TO astrosky_astronomy;

--
-- Name: activitylog_id_seq; Type: SEQUENCE; Schema: public; Owner: astrosky_astronomy
--

CREATE SEQUENCE public.activitylog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.activitylog_id_seq OWNER TO astrosky_astronomy;

--
-- Name: activitylog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: astrosky_astronomy
--

ALTER SEQUENCE public.activitylog_id_seq OWNED BY public.activitylog.id;


--
-- Name: botactions; Type: TABLE; Schema: public; Owner: astrosky_astronomy
--

CREATE TABLE public.botactions (
    id integer NOT NULL,
    indexed_at timestamp without time zone NOT NULL,
    did character varying(255) NOT NULL,
    type character varying(255) NOT NULL,
    stage character varying(255) NOT NULL,
    parent_uri character varying(255) NOT NULL,
    parent_cid character varying(255) NOT NULL,
    latest_uri character varying(255) NOT NULL,
    latest_cid character varying(255) NOT NULL,
    complete boolean DEFAULT false NOT NULL,
    authorized boolean DEFAULT false NOT NULL,
    checked_at timestamp without time zone NOT NULL
);


ALTER TABLE public.botactions OWNER TO astrosky_astronomy;

--
-- Name: botactions_id_seq; Type: SEQUENCE; Schema: public; Owner: astrosky_astronomy
--

CREATE SEQUENCE public.botactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.botactions_id_seq OWNER TO astrosky_astronomy;

--
-- Name: botactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: astrosky_astronomy
--

ALTER SEQUENCE public.botactions_id_seq OWNED BY public.botactions.id;


--
-- Name: modactions; Type: TABLE; Schema: public; Owner: astrosky_astronomy
--

CREATE TABLE public.modactions (
    id integer NOT NULL,
    indexed_at timestamp without time zone NOT NULL,
    did_mod character varying(255) NOT NULL,
    did_user character varying(255) NOT NULL,
    action character varying(255) NOT NULL,
    expiry timestamp without time zone
);


ALTER TABLE public.modactions OWNER TO astrosky_astronomy;

--
-- Name: modactions_id_seq; Type: SEQUENCE; Schema: public; Owner: astrosky_astronomy
--

CREATE SEQUENCE public.modactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.modactions_id_seq OWNER TO astrosky_astronomy;

--
-- Name: modactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: astrosky_astronomy
--

ALTER SEQUENCE public.modactions_id_seq OWNED BY public.modactions.id;


--
-- Name: normalizedfeedstats; Type: MATERIALIZED VIEW; Schema: public; Owner: astrosky_astronomy
--

CREATE MATERIALIZED VIEW public.normalizedfeedstats AS
 SELECT id,
    request_feed_uri,
    EXTRACT(isoyear FROM request_dt) AS year,
    EXTRACT(month FROM request_dt) AS month,
    EXTRACT(day FROM request_dt) AS day,
    EXTRACT(hour FROM request_dt) AS hour,
    EXTRACT(dow FROM request_dt) AS day_of_week
   FROM public.activitylog
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.normalizedfeedstats OWNER TO astrosky_astronomy;

--
-- Name: post; Type: TABLE; Schema: public; Owner: astrosky_astronomy
--

CREATE TABLE public.post (
    id integer NOT NULL,
    uri character varying(255) NOT NULL,
    cid character varying(255) NOT NULL,
    author character varying(255) NOT NULL,
    text character varying(500),
    feed_all boolean DEFAULT false NOT NULL,
    feed_astro boolean DEFAULT false NOT NULL,
    indexed_at timestamp without time zone NOT NULL,
    feed_exoplanets boolean DEFAULT false NOT NULL,
    feed_astrophotos boolean DEFAULT false NOT NULL,
    feed_cosmology boolean DEFAULT false NOT NULL,
    feed_extragalactic boolean DEFAULT false NOT NULL,
    feed_highenergy boolean DEFAULT false NOT NULL,
    feed_instrumentation boolean DEFAULT false NOT NULL,
    feed_methods boolean DEFAULT false NOT NULL,
    feed_milkyway boolean DEFAULT false NOT NULL,
    feed_planetary boolean DEFAULT false NOT NULL,
    feed_radio boolean DEFAULT false NOT NULL,
    feed_stellar boolean DEFAULT false NOT NULL,
    feed_education boolean DEFAULT false NOT NULL,
    feed_history boolean DEFAULT false NOT NULL,
    hidden boolean DEFAULT false NOT NULL,
    likes integer DEFAULT 0 NOT NULL,
    feed_research boolean DEFAULT false NOT NULL,
    feed_solar boolean DEFAULT false NOT NULL,
    feed_questions boolean DEFAULT false NOT NULL
);


ALTER TABLE public.post OWNER TO astrosky_astronomy;

--
-- Name: post_id_seq; Type: SEQUENCE; Schema: public; Owner: astrosky_astronomy
--

CREATE SEQUENCE public.post_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.post_id_seq OWNER TO astrosky_astronomy;

--
-- Name: post_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: astrosky_astronomy
--

ALTER SEQUENCE public.post_id_seq OWNED BY public.post.id;


--
-- Name: subscriptionstate; Type: TABLE; Schema: public; Owner: astrosky_astronomy
--

CREATE TABLE public.subscriptionstate (
    id integer NOT NULL,
    service character varying(255) NOT NULL,
    cursor bigint NOT NULL
);


ALTER TABLE public.subscriptionstate OWNER TO astrosky_astronomy;

--
-- Name: subscriptionstate_id_seq; Type: SEQUENCE; Schema: public; Owner: astrosky_astronomy
--

CREATE SEQUENCE public.subscriptionstate_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subscriptionstate_id_seq OWNER TO astrosky_astronomy;

--
-- Name: subscriptionstate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: astrosky_astronomy
--

ALTER SEQUENCE public.subscriptionstate_id_seq OWNED BY public.subscriptionstate.id;


--
-- Name: account id; Type: DEFAULT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.account ALTER COLUMN id SET DEFAULT nextval('public.account_id_seq'::regclass);


--
-- Name: activitylog id; Type: DEFAULT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.activitylog ALTER COLUMN id SET DEFAULT nextval('public.activitylog_id_seq'::regclass);


--
-- Name: botactions id; Type: DEFAULT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.botactions ALTER COLUMN id SET DEFAULT nextval('public.botactions_id_seq'::regclass);


--
-- Name: modactions id; Type: DEFAULT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.modactions ALTER COLUMN id SET DEFAULT nextval('public.modactions_id_seq'::regclass);


--
-- Name: post id; Type: DEFAULT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.post ALTER COLUMN id SET DEFAULT nextval('public.post_id_seq'::regclass);


--
-- Name: subscriptionstate id; Type: DEFAULT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.subscriptionstate ALTER COLUMN id SET DEFAULT nextval('public.subscriptionstate_id_seq'::regclass);


--
-- Name: account account_pkey; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);


--
-- Name: activitylog activitylog_pkey; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.activitylog
    ADD CONSTRAINT activitylog_pkey PRIMARY KEY (id);


--
-- Name: botactions botactions_pkey; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.botactions
    ADD CONSTRAINT botactions_pkey PRIMARY KEY (id);


--
-- Name: modactions modactions_pkey; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.modactions
    ADD CONSTRAINT modactions_pkey PRIMARY KEY (id);


--
-- Name: post post_pkey; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.post
    ADD CONSTRAINT post_pkey PRIMARY KEY (id);


--
-- Name: subscriptionstate subscriptionstate_pkey; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.subscriptionstate
    ADD CONSTRAINT subscriptionstate_pkey PRIMARY KEY (id);


--
-- Name: subscriptionstate subscriptionstate_service_key; Type: CONSTRAINT; Schema: public; Owner: astrosky_astronomy
--

ALTER TABLE ONLY public.subscriptionstate
    ADD CONSTRAINT subscriptionstate_service_key UNIQUE (service);


--
-- Name: account_did; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_did ON public.account USING btree (did);


--
-- Name: account_handle; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_handle ON public.account USING btree (handle);


--
-- Name: account_indexed_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_indexed_at ON public.account USING btree (indexed_at);


--
-- Name: account_is_banned; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_is_banned ON public.account USING btree (is_banned);


--
-- Name: account_is_muted; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_is_muted ON public.account USING btree (is_muted);


--
-- Name: account_is_valid; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_is_valid ON public.account USING btree (is_valid);


--
-- Name: account_mod_level; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX account_mod_level ON public.account USING btree (mod_level);


--
-- Name: activitylog_request_dt; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX activitylog_request_dt ON public.activitylog USING btree (request_dt);


--
-- Name: activitylog_request_feed_uri; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX activitylog_request_feed_uri ON public.activitylog USING btree (request_feed_uri);


--
-- Name: activitylog_request_user_did; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX activitylog_request_user_did ON public.activitylog USING btree (request_user_did);


--
-- Name: botactions_authorized; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX botactions_authorized ON public.botactions USING btree (authorized);


--
-- Name: botactions_checked_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX botactions_checked_at ON public.botactions USING btree (checked_at);


--
-- Name: botactions_complete; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX botactions_complete ON public.botactions USING btree (complete);


--
-- Name: botactions_indexed_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX botactions_indexed_at ON public.botactions USING btree (indexed_at);


--
-- Name: botactions_stage; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX botactions_stage ON public.botactions USING btree (stage);


--
-- Name: botactions_type; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX botactions_type ON public.botactions USING btree (type);


--
-- Name: idx_account_account_did_is_valid; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_account_account_did_is_valid ON public.account USING btree (did, is_valid);


--
-- Name: idx_account_account_handle; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_account_account_handle ON public.account USING btree (handle);


--
-- Name: idx_account_account_is_banned; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_account_account_is_banned ON public.account USING btree (is_banned);


--
-- Name: idx_account_account_is_muted; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_account_account_is_muted ON public.account USING btree (is_muted);


--
-- Name: idx_account_account_is_valid; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_account_account_is_valid ON public.account USING btree (is_valid);


--
-- Name: idx_account_account_mod_level; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_account_account_mod_level ON public.account USING btree (mod_level);


--
-- Name: idx_activitylog_request_dt_index; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_activitylog_request_dt_index ON public.activitylog USING btree (request_dt);


--
-- Name: idx_activitylog_request_feed_uri_index; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_activitylog_request_feed_uri_index ON public.activitylog USING btree (request_feed_uri);


--
-- Name: idx_activitylog_request_user_did_index; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_activitylog_request_user_did_index ON public.activitylog USING btree (request_user_did);


--
-- Name: idx_botactions_botactions_authorized; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_botactions_botactions_authorized ON public.botactions USING btree (authorized);


--
-- Name: idx_botactions_botactions_checked_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_botactions_botactions_checked_at ON public.botactions USING btree (checked_at);


--
-- Name: idx_botactions_botactions_complete; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_botactions_botactions_complete ON public.botactions USING btree (complete);


--
-- Name: idx_botactions_botactions_indexed_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_botactions_botactions_indexed_at ON public.botactions USING btree (indexed_at);


--
-- Name: idx_botactions_botactions_stage; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_botactions_botactions_stage ON public.botactions USING btree (stage);


--
-- Name: idx_botactions_botactions_type; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_botactions_botactions_type ON public.botactions USING btree (type);


--
-- Name: idx_modactions_modactions_action; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_modactions_modactions_action ON public.modactions USING btree (action);


--
-- Name: idx_modactions_modactions_did_mod; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_modactions_modactions_did_mod ON public.modactions USING btree (did_mod);


--
-- Name: idx_modactions_modactions_did_user; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_modactions_modactions_did_user ON public.modactions USING btree (did_user);


--
-- Name: idx_modactions_modactions_expiry; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_modactions_modactions_expiry ON public.modactions USING btree (expiry);


--
-- Name: idx_modactions_modactions_indexed_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_modactions_modactions_indexed_at ON public.modactions USING btree (indexed_at);


--
-- Name: idx_normalized_feed_stats_id; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE UNIQUE INDEX idx_normalized_feed_stats_id ON public.normalizedfeedstats USING btree (id);


--
-- Name: idx_post_cid; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_cid ON public.post USING btree (cid);


--
-- Name: idx_post_feed_questions; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_feed_questions ON public.post USING btree (feed_questions);


--
-- Name: idx_post_feed_research; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_feed_research ON public.post USING btree (feed_research);


--
-- Name: idx_post_feed_solar; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_feed_solar ON public.post USING btree (feed_solar);


--
-- Name: idx_post_post_author; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_author ON public.post USING btree (author);


--
-- Name: idx_post_post_feed_all; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_all ON public.post USING btree (feed_all);


--
-- Name: idx_post_post_feed_astro; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_astro ON public.post USING btree (feed_astro);


--
-- Name: idx_post_post_feed_astrophotos; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_astrophotos ON public.post USING btree (feed_astrophotos);


--
-- Name: idx_post_post_feed_cosmology; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_cosmology ON public.post USING btree (feed_cosmology);


--
-- Name: idx_post_post_feed_education; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_education ON public.post USING btree (feed_education);


--
-- Name: idx_post_post_feed_exoplanets; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_exoplanets ON public.post USING btree (feed_exoplanets);


--
-- Name: idx_post_post_feed_extragalactic; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_extragalactic ON public.post USING btree (feed_extragalactic);


--
-- Name: idx_post_post_feed_highenergy; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_highenergy ON public.post USING btree (feed_highenergy);


--
-- Name: idx_post_post_feed_history; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_history ON public.post USING btree (feed_history);


--
-- Name: idx_post_post_feed_instrumentation; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_instrumentation ON public.post USING btree (feed_instrumentation);


--
-- Name: idx_post_post_feed_methods; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_methods ON public.post USING btree (feed_methods);


--
-- Name: idx_post_post_feed_milkyway; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_milkyway ON public.post USING btree (feed_milkyway);


--
-- Name: idx_post_post_feed_planetary; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_planetary ON public.post USING btree (feed_planetary);


--
-- Name: idx_post_post_feed_radio; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_radio ON public.post USING btree (feed_radio);


--
-- Name: idx_post_post_feed_stellar; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_feed_stellar ON public.post USING btree (feed_stellar);


--
-- Name: idx_post_post_hidden; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_hidden ON public.post USING btree (hidden);


--
-- Name: idx_post_post_indexed_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_indexed_at ON public.post USING btree (indexed_at);


--
-- Name: idx_post_post_uri; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX idx_post_post_uri ON public.post USING btree (uri);


--
-- Name: modactions_action; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX modactions_action ON public.modactions USING btree (action);


--
-- Name: modactions_did_mod; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX modactions_did_mod ON public.modactions USING btree (did_mod);


--
-- Name: modactions_did_user; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX modactions_did_user ON public.modactions USING btree (did_user);


--
-- Name: modactions_expiry; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX modactions_expiry ON public.modactions USING btree (expiry);


--
-- Name: modactions_indexed_at; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX modactions_indexed_at ON public.modactions USING btree (indexed_at);


--
-- Name: normalizedfeedstats_day; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX normalizedfeedstats_day ON public.normalizedfeedstats USING btree (day);


--
-- Name: normalizedfeedstats_day_of_week; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX normalizedfeedstats_day_of_week ON public.normalizedfeedstats USING btree (day_of_week);


--
-- Name: normalizedfeedstats_hour; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX normalizedfeedstats_hour ON public.normalizedfeedstats USING btree (hour);


--
-- Name: normalizedfeedstats_month; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX normalizedfeedstats_month ON public.normalizedfeedstats USING btree (month);


--
-- Name: normalizedfeedstats_request_feed_uri; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX normalizedfeedstats_request_feed_uri ON public.normalizedfeedstats USING btree (request_feed_uri);


--
-- Name: normalizedfeedstats_year; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE INDEX normalizedfeedstats_year ON public.normalizedfeedstats USING btree (year);


--
-- Name: subscriptionstate_service; Type: INDEX; Schema: public; Owner: astrosky_astronomy
--

CREATE UNIQUE INDEX subscriptionstate_service ON public.subscriptionstate USING btree (service);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

