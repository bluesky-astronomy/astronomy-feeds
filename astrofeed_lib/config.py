"""Package configuration. For now, it just takes from environment variables."""
import os


# --- HOST CONFIGURATION ----------------------
# Server host variables
SERVICE_DID = os.environ.get('SERVICE_DID', None)
HOSTNAME = os.environ.get('HOSTNAME', None)
if HOSTNAME is None:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')
if SERVICE_DID is None:
    SERVICE_DID = f'did:web:{HOSTNAME}'

# --- FEED CONFIGURATION ----------------------
# Feed variables
FEED_URI = "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/"

# Dict containing all feeds *to be published*! key:value pairs of the short name and name as published.
# The short name is used throughout databases. The name as published is the URI where the feed is.
# The actual inner workings of feeds are housed in feeds.py. This variable specifies which feeds the firehose and
# server should try to host, however.
FEED_URIS = {
    "all": FEED_URI + "astro-all",
    "astro": FEED_URI + "astro",
}

# Dict containing all terms to search for in strings
FEED_TERMS = {
    "all": None,
    "astro": ("🔭", "#astro", "#astronomy"),
    # "exoplanets": ("🪐", "#exoplanet", "#exoplanets"),
    # "planetary": ("🌍", "🌎", "🌏", "#planetaryscience", "#planetsci"),
    # "stars": ("⭐", "#star", "#stars"),
    # "astrophotos": ("🔭📷", "#astrophotos", "#astrophotography"),
}


# --- ACCOUNT SYSTEM CONFIGURATION ----------------------
# Bluesky client integration for DID queries
HANDLE = "emily.space"  # os.getenv("BLUESKY_HANDLE")
PASSWORD = os.getenv("BLUESKY_PASSWORD")
if HANDLE is None or PASSWORD is None:
    raise ValueError("Bluesky account environment variables not set.")

# Google Sheets integration
SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aUjkLr5uzoVQuT8Iy_7QpmkdSfCXuR7S3MV3-zYKnFk/export?format=csv&gid=1795057871"
QUERY_INTERVAL = 60 * 10

# --- DATABASE CONFIGURATION ----------------------
# Database stuff
DATABASE_HOST = os.environ.get('DATABASE_HOST', None)
DATABASE_PORT = os.environ.get('DATABASE_PORT', 25060)
DATABASE_USER = os.environ.get('DATABASE_USER', None)
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', None)
DATABASE_NAME = os.environ.get('DATABASE_NAME')
if DATABASE_HOST is None or DATABASE_USER is None or DATABASE_PASSWORD is None or DATABASE_NAME is None:
    raise ValueError("You must specify a database to use!")
