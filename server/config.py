import os

# Todo this is the worst code ever. Needs a better system
# Server host variables
SERVICE_DID = os.environ.get('SERVICE_DID', None)
HOSTNAME = os.environ.get('HOSTNAME', None)

if HOSTNAME is None:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

if SERVICE_DID is None:
    SERVICE_DID = f'did:web:{HOSTNAME}'

# Feed variables
URI_ASTRO_ALL = "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/astro-all"  # os.environ.get('URI_ASTRO_ALL')
URI_ASTRO = "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/astro"  # os.environ.get('URI_ASTRO')
if URI_ASTRO_ALL is None or URI_ASTRO is None:
    raise RuntimeError('Publish your feed first (run publish_feed.py) to obtain Feed URI.')

# Bluesky client integration for DID queries
HANDLE = "emily.space"  # os.getenv("BLUESKY_HANDLE")
PASSWORD = os.getenv("BLUESKY_PASSWORD")
if HANDLE is None or PASSWORD is None:
    raise ValueError("Bluesky account environment variables not set.")

# Google Sheets integration
SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aUjkLr5uzoVQuT8Iy_7QpmkdSfCXuR7S3MV3-zYKnFk/export?format=csv&gid=1795057871"
QUERY_INTERVAL = 60 * 10

# Database stuff
DATABASE_HOST = os.environ.get('DATABASE_HOST', None)
DATABASE_PORT = os.environ.get('DATABASE_PORT', 25060)
DATABASE_USER = os.environ.get('DATABASE_USER', None)
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', None)
DATABASE_NAME = os.environ.get('DATABASE_NAME')
if DATABASE_HOST is None or DATABASE_USER is None or DATABASE_PASSWORD is None or DATABASE_NAME is None:
    raise ValueError("You must specify a database to use!")
