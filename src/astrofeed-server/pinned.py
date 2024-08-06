import random

# DIDs
# emily.space: did:plc:jcoy7v3a2t4rcfdh6i4kza25
# astronomy.blue: did:plc:xy2zorw2ys47poflotxthlzg


# Pinned posts dict, where:
# - keys are a link to the post in ATProto format
# - values are the post weight (higher = more likely to be shown)
PINNED_POSTS = {    
    "at://did:plc:xy2zorw2ys47poflotxthlzg/app.bsky.feed.post/3kyzye4lujs2w": 2.5,  # Signup instructions
    # # "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kkrhwzmhg22i": 1.5,  # 'Bluesky is open now'
    "at://did:plc:xy2zorw2ys47poflotxthlzg/app.bsky.feed.post/3kyxng2wims2n": 1.5,  # List of all feeds
    "at://did:plc:xy2zorw2ys47poflotxthlzg/app.bsky.feed.post/3kyxnyimjna2a": 0.5,  # Like the feed pls
    "at://did:plc:xy2zorw2ys47poflotxthlzg/app.bsky.feed.post/3kyxobfx76e2n": 1.5,  # Getting started guide
}

def add_pinned_post_to_feed(body):
    post = random.choices(population=list(PINNED_POSTS.keys()), weights=list(PINNED_POSTS.values()))[0]
    body["feed"].insert(0, {"post": post})
