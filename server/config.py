import os

SERVICE_DID = os.environ.get('SERVICE_DID', None)
HOSTNAME = os.environ.get('HOSTNAME', None)

if HOSTNAME is None:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

if SERVICE_DID is None:
    SERVICE_DID = f'did:web:{HOSTNAME}'

WHATS_ALF_URI = os.environ.get('WHATS_ALF_URI')
if WHATS_ALF_URI is None:
    raise RuntimeError('Publish your feed first (run publish_feed.py) to obtain Feed URI. '
                       'Set this URI to "WHATS_ALF_URI" environment variable.')

HANDLE = os.getenv("BLUESKY_HANDLE")
PASSWORD = os.getenv("BLUESKY_PASSWORD")

if HANDLE is None or PASSWORD is None:
    raise ValueError("Bluesky account environment variables not set.")

SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aUjkLr5uzoVQuT8Iy_7QpmkdSfCXuR7S3MV3-zYKnFk/export?format=csv&gid=1795057871"
QUERY_INTERVAL = 60 * 10
