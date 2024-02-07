"""Logic for how commits are filtered."""
import logging
from astrofeed_lib.database import db, Post
from astrofeed_lib.feeds import post_in_feeds


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def operations_callback(
    ops: dict, cursor: int, valid_accounts: set, existing_posts: set
) -> list:
    # See how many posts are valid
    posts_to_create = []
    valid_posts = [
        post for post in ops["posts"]["created"] if post["author"] in valid_accounts
    ]

    # Classify valid posts into feed categories
    feed_counts = {}
    for created_post in valid_posts:
        # Don't add a post if it already exists (e.g. if we're looping over the firehose)
        if created_post["uri"] in existing_posts:
            logger.info(f"Ignored duplicate post (cursor={cursor})")
            continue

        # Basic post info to add to the database
        post_text = created_post["record"]["text"]
        post_dict = {
            "uri": created_post["uri"],
            "cid": created_post["cid"],
            "author": created_post["author"],
            "text": post_text,
        }

        # Add labels to the post for
        feed_labels = post_in_feeds(post_text)
        post_dict.update(feed_labels)
        posts_to_create.append(post_dict)

        # Count how many posts we have
        # Initialise the dict if we're here the first time (not done above for optimization reasons)
        if len(feed_counts) == 0:
            feed_counts = {key: 0 for key in feed_labels}

        # Add feed labelling to said dict
        for a_key in feed_labels:
            feed_counts[a_key] += feed_labels[a_key]

    # See if there are any posts that need deleting
    posts_to_delete = [
        post["uri"]
        for post in ops["posts"]["deleted"]
        if post["uri"] in existing_posts
    ]

    # Perform database operations
    if posts_to_delete or posts_to_create:
        db.connect(reuse_if_open=True)

        if posts_to_delete:
            Post.delete().where(Post.uri.in_(posts_to_delete))
            # existing_posts.remove(posts_to_delete)
            logger.info(f"Deleted posts: {len(posts_to_delete)} (cursor={cursor})")

        if posts_to_create:
            with db.atomic():
                for post_dict in posts_to_create:
                    Post.create(**post_dict)
            # existing_posts.add([x["uri"] for x in posts_to_create])
            feed_counts_string = ", ".join(
                [f"{key[5:]}-{feed_counts[key]}" for key in feed_counts]
            )
            logger.info(f"Added posts: {feed_counts_string} (cursor={cursor})")

        db.close()

    if not posts_to_create:
        return []
    return [post["uri"] for post in posts_to_create]
