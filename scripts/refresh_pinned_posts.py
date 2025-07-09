"""Refreshes pinned posts for all of the feeds, and writes them to a file.

See https://github.com/MarshalX/atproto/blob/main/examples/advanced_usage/send_ogp_link_card.py
for better methods to get open graph metadata
"""

import astrofeed_lib
import os
from astrofeed_lib.config import FEED_TERMS, FEED_NAMING_SCHEME_RULEBREAKERS
from astrofeed_lib.client import get_client
from atproto import client_utils, models
from pathlib import Path
import time
import httpx
import re
from PIL import Image
import io
import json


FEED_NAMING_SCHEME_RULEBREAKERS_REVERSED = {
    v: k for k, v in FEED_NAMING_SCHEME_RULEBREAKERS.items()
}

FEEDS_WITH_NO_DESCRIPTION = {"questions", "signup"}


# Todo refactor into the config section somehow
FEED_DESCRIPTIONS = {
    "all": "all posts from all signed up users of the Astronomy feeds.",
    "astro": "astronomy posts, by astronomers!",
    "astrophotos": "astrophotography posts on Bluesky.",
    "research": "posts about astronomy, astrophysics, and planetary science research.",
    "cosmology": "posts about cosmology research.",
    "exoplanets": "posts about research on exoplanets.",
    "extragalactic": "posts about research on extragalactic galaxies and phenomena.",
    "highenergy": "posts about high-energy astrophysics.",
    "instrumentation": "posts about instrumentation for astronomy.",
    "methods": "posts about software and statistics for astronomy.",
    "milkyway": "posts about Galactic and Milky Way astronomy.",
    "planetary": "posts about planetary science.",
    "radio": "posts about radio astronomy.",
    "solar": "posts about heliophysics.",
    "stellar": "posts about stellar physics.",
    "education": "posts about astronomy education.",
    "history": "posts about the history of astronomy and astrophysics.",
}


# Setup & variables
handle = os.getenv("BLUESKY_HANDLE")
password = os.getenv("BLUESKY_PASSWORD")
outdir = Path(astrofeed_lib.__path__[0]) / "data"
client = get_client(handle, password)


# Fetch a name for each feed
feedInfoBluesky = client.app.bsky.feed.get_actor_feeds(
    params=dict(actor="did:plc:jcoy7v3a2t4rcfdh6i4kza25")
)


# Some helpers
def fetch_open_graph_information(feed):
    # page = request.urlopen(f"https://astrosky.eco/faq/{feed}").read().decode('utf8')
    page = httpx.get(f"https://astrosky.eco/faq/{feed}").text
    title = (
        re.findall(r'<meta property="og:title" content="[\s\S]*?"\/>', page)[0]
        .replace('<meta property="og:title" content="', "")
        .replace('"/>', "")
    )
    description = (
        re.findall(r'<meta property="og:description" content="[\s\S]*?"\/>', page)[0]
        .replace('<meta property="og:description" content="', "")
        .replace('"/>', "")
        .replace("&amp;", "&")
    )
    url = (
        re.findall(r'<meta property="og:url" content="[\s\S]*?"\/>', page)[0]
        .replace('<meta property="og:url" content="', "")
        .replace('"/>', "")
    )
    image = (
        re.findall(r'<meta property="og:image" content="[\s\S]*?"\/>', page)[0]
        .replace('<meta property="og:image" content="', "")
        .replace('"/>', "")
    )
    return title, description, url, image


def resize_image(img_data, max_size_kb=900):
    """Resizes an image to fit Bluesky specs."""

    location = Path("./temp.jpg")
    im = Image.open(io.BytesIO(img_data))
    im = im.convert("RGB")
    quality = 100
    while True:
        im.save(location, quality=quality)
        quality -= 5
        if location.stat().st_size < 1024 * max_size_kb:
            break
        if quality <= 0:
            raise RuntimeError("Unable to make image small enough!")
        
    with open(location, 'rb') as handle:
        img_data = handle.read()
    os.remove(location)
    return img_data


# Make posts!
def create_pinned_post(feed):
    short_name = feed.uri.split("/")[-1]
    url = f"https://bsky.app/profile/did:plc:jcoy7v3a2t4rcfdh6i4kza25/feed/{short_name}"

    # Change short_name to not have rule break
    if short_name in FEED_NAMING_SCHEME_RULEBREAKERS_REVERSED:
        short_name = FEED_NAMING_SCHEME_RULEBREAKERS_REVERSED[short_name]

    print("------------------------------------------")
    print(f"Creating pinned post for feed {short_name}")
    print("------------------------------------------")

    # Create a nice display name
    display_name = feed.display_name.replace("The", "").strip()

    # Work out what feed criteria we have (if any)
    criteria = ""
    if short_name in FEED_TERMS:
        if FEED_TERMS[short_name] is not None:
            criteria = ", ".join(
                FEED_TERMS[short_name]["emoji"] + FEED_TERMS[short_name]["words"]
            )
            criteria = " or".join(criteria.rsplit(",", 1))  # Change last ',' to 'or'
            criteria = f"• Posts containing {criteria} are included.\n"

    # Construct text & embed to send
    text = "This feed exists for technical purposes."
    embed = None
    if short_name not in FEEDS_WITH_NO_DESCRIPTION:
        text = (
            client_utils.TextBuilder()
            .text("Welcome to the ")
            .link(f"{display_name}", url)
            .text(f" feed! Contains {FEED_DESCRIPTIONS[short_name]}\n\n")
            .text(criteria)
            .text("• You need to ")
            .link("sign up", "https://astrosky.eco/about/signup")
            .text(" for your posts to appear here.\n")
            .text("• We have ")
            .link("many other", "https://astrosky.eco/feeds")
            .text(" astro-related feeds!")
            .text("\n\n")
            .text("See the FAQ for more info:")
        )

        title, description, url, image = fetch_open_graph_information(short_name)

        # Upload image blob
        img_data = httpx.get(image).content
        img_data = resize_image(img_data)
        thumb_blob = client.upload_blob(img_data).blob

        embed = models.AppBskyEmbedExternal.Main(
            external=models.AppBskyEmbedExternal.External(
                description=description,
                title=title,
                uri=url,
                thumb=thumb_blob
            )
        )

    # Send it!
    response = client.send_post(text, embed=embed)
    time.sleep(1)
    return short_name, response.uri

uris = {}
for feed in feedInfoBluesky.feeds:
    name, uri = create_pinned_post(feed)
    uris[name] = uri

with open(outdir / "pinned_posts.json", 'w') as handle:
    json.dump(uris, handle)

print(uris)

# print(feeds)
