#!/usr/bin/env python3
# YOU MUST INSTALL ATPROTO SDK
# pip3 install atproto

from datetime import datetime
from atproto.xrpc_client.models import ids
from atproto import Client, models
import os

# YOUR bluesky handle
# Ex: user.bsky.social
HANDLE: str = "emily.space"

# # YOUR bluesky password, or preferably an App Password (found in your client settings)
# # Ex: abcd-1234-efgh-5678
# PASSWORD: str = ''

# The hostname of the server where feed server will be hosted
# Ex: feed.bsky.dev
HOSTNAME: str = "feed-all.astronomy.blue"

# A short name for the record that will show in urls
# Lowercase with no spaces.
# Ex: whats-hot
RECORD_NAME: str = "exoplanets"

# A display name for your feed
# Ex: What's Hot
DISPLAY_NAME: str = "Exoplanets"

# (Optional) A description of your feed
# Ex: Top trending content from the whole network
DESCRIPTION: str = "Exoplanet posts on Bluesky! Part of the Astronomy feeds network.\nAstronomers can sign up to post here: https://signup.astronomy.blue\nContains posts from registered users with a 🪐, #exoplanet, or #exoplanets."

# (Optional) The path to an image to be used as your feed's avatar
# Ex: ./path/to/avatar.jpeg
AVATAR_PATH: str = "../images/exoplanets.jpg"

# (Optional). Only use this if you want a service did different from did:web
SERVICE_DID: str = ""


# -------------------------------------
# NO NEED TO TOUCH ANYTHING BELOW HERE
# -------------------------------------


def main():
    client = Client()
    # password = input("Enter your app password: ")
    password = os.getenv("BLUESKY_PASSWORD")
    client.login(HANDLE, password)

    feed_did = SERVICE_DID
    if not feed_did:
        feed_did = f"did:web:{HOSTNAME}"

    avatar_blob = None
    if AVATAR_PATH:
        with open(AVATAR_PATH, "rb") as f:
            avatar_data = f.read()
            avatar_blob = client.com.atproto.repo.upload_blob(avatar_data, timeout=30).blob

    response = client.com.atproto.repo.put_record(
        models.ComAtprotoRepoPutRecord.Data(
            repo=client.me.did,
            collection=ids.AppBskyFeedGenerator,
            rkey=RECORD_NAME,
            record=models.AppBskyFeedGenerator.Main(
                did=feed_did,
                displayName=DISPLAY_NAME,
                description=DESCRIPTION,
                avatar=avatar_blob,
                createdAt=datetime.now().isoformat(),
            ),
        )
    )

    print("Successfully published!")
    print('Feed URI (put in "WHATS_ALF_URI" env var):', response.uri)


if __name__ == "__main__":
    main()
