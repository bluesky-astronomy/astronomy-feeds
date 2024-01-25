import random

PINNED_POSTS = {
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kc632qlmnm2j": 1.5,  # Signup instructions
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kdheyu7hct24": 0.5,  # Exoplanet feed announcement
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kdtlml2mvf2z": 0.5,  # Astrophotography feed announcement
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kdhfpnyeff2c": 0.5,  # Like the feed pls
}

def add_pinned_post_to_feed(body):
    post = random.choices(population=list(PINNED_POSTS.keys()), weights=list(PINNED_POSTS.values()))[0]
    body["feed"].insert(0, {"post": post})
