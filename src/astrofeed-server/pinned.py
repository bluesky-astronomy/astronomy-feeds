import random

PINNED_POSTS = {    
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kc632qlmnm2j": 2.5,  # Signup instructions
    # # "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kkrhwzmhg22i": 1.5,  # 'Bluesky is open now'
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kkri5olz3526": 1.5,  # List of all feeds
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kkrivv43ve2z": 0.5,  # Like the feed pls
    "at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.post/3kkris4cvel2o": 1.5,  # Getting started guide
}

def add_pinned_post_to_feed(body):
    post = random.choices(population=list(PINNED_POSTS.keys()), weights=list(PINNED_POSTS.values()))[0]
    body["feed"].insert(0, {"post": post})
