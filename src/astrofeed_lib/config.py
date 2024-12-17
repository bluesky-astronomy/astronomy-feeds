"""Package configuration. For now, it just takes from environment variables."""

import os


################################################
# ENVIRONMENT VARIABLE SETTINGS
#
# These settings control things common to many modulues, including the database spec.
################################################

# ----------------------------------------------
# PRODUCTION MODE
# ----------------------------------------------
# Whether or not we're in production mode. Within this module, production mode causes
# the following things:
# 1. We expect a remote MySQL database instead of a local SQLite one
ASTROFEED_PRODUCTION = bool(os.getenv("ASTROFEED_PRODUCTION", False))


# ----------------------------------------------
# DATABASE CONFIGURATION
# ----------------------------------------------
BLUESKY_DATABASE = os.environ.get("BLUESKY_DATABASE", None)


################################################
# FEED SETTINGS
#
# In principle, everything in this second half of the file should rarely need changing.
# These are things that aren't set on the go, but rather are core settings of the whole
# Astronomy feeds architecture.
################################################

# ----------------------------------------------
# HOST CONFIGURATION
# ----------------------------------------------
# Server host variables for astrofeed-server - i.e., where on the internet our ATProto
# endpoints live
# Todo: these should probably live in the Flask app, as it's the only place where they're used
HOSTNAME = "feed-all.astronomy.blue"
SERVICE_DID = f"did:web:{HOSTNAME}"

# ----------------------------------------------
# FEED CONFIGURATION
# ----------------------------------------------
# URI where the feed enpoints live in the ATProtocol universe. They are all currently
# tied to @emily.space's DID.
FEED_URI = "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/"

# Dict containing all terms to search for in strings
# There are two options here: a feed may either have 'None' (all posts added) OR a dict
# containing emoji combinations and words. Emoji are accepted anywhere in a post;
# whereas words have to be exact space-separated matches (e.g. #space won't match
# #spacecraft, but it would if it was in the emoji section)
# These feed terms also interact with the database specification. The Post table in the
# database contains boolean columns feed_all, feed_astro, ... etc for each one of the
# feeds.
FEED_TERMS = {
    # "EXAMPLE": {"emoji": [], "words": []},
    # MAIN FEEDS
    "all": None,
    "astro": {"emoji": ["🔭"], "words": ["#astro", "#astronomy"]},
    "astrophotos": {
        "emoji": [],
        "words": ["#astrophoto", "#astrophotos", "#astrophotography"],
    },
    # ASTRONOMY TOPICS
    "cosmology": {"emoji": [], "words": ["#cosmology"]},
    "exoplanets": {"emoji": ["🪐"], "words": ["#exoplanet", "#exoplanets"]},
    "extragalactic": {"emoji": [], "words": ["#extragalactic"]},
    "highenergy": {"emoji": [], "words": ["#highenergyastro"]},
    "instrumentation": {"emoji": [], "words": ["#instrumentation"]},
    "methods": {"emoji": [], "words": ["#astromethods", "#astrocoding", "#astrocode"]},
    "milkyway": {"emoji": [], "words": ["#milkyway"]},
    "planetary": {"emoji": [], "words": ["#planetaryscience", "#planetsci"]},
    "radio": {"emoji": [], "words": ["#radioastronomy", "#radioastro"]},
    # "solar": {"emoji": [], "words": ["#solarastronomy", "#solarastro", "#thesun"]},
    "stellar": {
        "emoji": [],
        "words": ["#stars", "#stellarastrononomy", "#stellarastro"],
    },
    # ASTRONOMY / OTHER
    "education": {"emoji": [], "words": ["#astroeducation", "#astroedu"]},
    "history": {"emoji": [], "words": ["#astrohistory", "#historyofastronomy"]},
    # "questions": {"emoji": [], "words": ["#askanastronomer"]},
}

# These are a number of feeds that aren't from the firehose but are hosted on the same
# server. The astrofeed-server Flask app hosts them.
NON_FIREHOSE_FEEDS = {"signup": {"emoji": [], "words": []}}

# Dict containing all feeds *to be published*! key:value pairs of the name as published
# and internal (short) name. The short name is used throughout databases. The name as
# published is the URI where the feed is.
# The actual inner workings of feeds are housed in feeds.py. This variable specifies
# which feeds the astrofeed-server should try to host.
# Todo: consider moving these variables to astrofeed-server, as they're really for that
FEED_NAMING_SCHEME_RULEBREAKERS = {
    "all": "astro-all"
}  # The astrosky feed has an inconsistent name!
FEED_URIS = {}
for a_feed in (FEED_TERMS | NON_FIREHOSE_FEEDS).keys():
    if a_feed in FEED_NAMING_SCHEME_RULEBREAKERS:
        key = FEED_URI + FEED_NAMING_SCHEME_RULEBREAKERS[a_feed]
    else:
        key = FEED_URI + a_feed
    FEED_URIS[key] = a_feed
