"""Logic for how commits are filtered."""

# import logging
from astrofeed_lib.database import (
    Post,
    get_database,
    setup_connection,
    teardown_connection,
)
from astrofeed_lib.accounts import CachedAccountQuery
from astrofeed_lib.posts import CachedPostQuery
from astrofeed_lib.feeds import post_in_feeds
from atproto import CAR, AtUri
from atproto import models


# This is our set of accounts that are signed up, including those that are muted/banned
# (as those could be later reversed.) We keep it updated once every 60 seconds.
VALID_ACCOUNTS = CachedAccountQuery(query_interval=60)

# We keep a set of existing posts around to try and reduce our chances of adding duplicates.
EXISTING_POSTS = CachedPostQuery(query_interval=300)


def apply_commit(
    commit: models.ComAtprotoSyncSubscribeRepos.Commit,
):
    """Applies the operations in a commit based on which ones are necessary to process."""
    # Sort the initial commit into everything we're interested in
    ops = _get_ops_by_type(commit)
    posts_to_create, posts_to_delete = _get_required_ops(ops)
    if not posts_to_create and not posts_to_delete:
        return

    # If we have posts to create, then we'll also need to classify them
    posts_to_create_classified, feed_counts = _classify_posts(posts_to_create)

    # Perform database operations
    cursor = commit.seq
    setup_connection(get_database())
    _delete_posts(cursor, posts_to_delete)
    _create_posts(cursor, posts_to_create_classified, feed_counts)
    teardown_connection(get_database())


def _create_posts(cursor, posts_to_create_classified, feed_counts):
    """Adds posts to the database."""
    if posts_to_create_classified:
        # Todo still not infallible against adding duplicate posts
        with get_database().atomic():
            for post_dict in posts_to_create_classified:
                Post.create(**post_dict)
        feed_counts_string = ", ".join(
            [f"{key[5:]}-{feed_counts[key]}" for key in feed_counts]
        )
        print(f"Added posts: {feed_counts_string} (cursor={cursor})")


def _delete_posts(cursor, posts_to_delete):
    """Removes posts from the database."""
    if posts_to_delete:
        # Todo needs fixing
        Post.delete().where(Post.uri.in_(posts_to_delete))  # type: ignore
        print(f"Deleted posts: {len(posts_to_delete)} (cursor={cursor})")


def _classify_posts(posts_to_create):
    """Classifies posts by type, also returning a dictionary of post classifications
    for some pretty printing of the added posts.
    """
    feed_counts = {}
    posts_to_create_classified = []
    for created_post in posts_to_create:
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
        posts_to_create_classified.append(post_dict)

        # Count how many posts we have
        # Initialise the dict if we're here the first time (not done above for optimization reasons)
        if len(feed_counts) == 0:
            feed_counts = {key: 0 for key in feed_labels}

        # Add feed labelling to said dict
        for a_key in feed_labels:
            feed_counts[a_key] += feed_labels[a_key]
    return posts_to_create_classified, feed_counts


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> dict:  # noqa: C901
    """Sorts all commits/operations by type into a convenient to process dictionary."""
    operation_by_type = {
        "posts": {"created": [], "deleted": []},
        "reposts": {"created": [], "deleted": []},
        "likes": {"created": [], "deleted": []},
        "follows": {"created": [], "deleted": []},
    }

    # Handle occasional empty commit (not in ATProto spec but seems to happen sometimes.
    # Can be a blank binary string sometimes, for no reason)
    if not commit.blocks:
        return operation_by_type

    car = CAR.from_bytes(commit.blocks)  # type: ignore

    for op in commit.ops:
        uri = AtUri.from_str(f"at://{commit.repo}/{op.path}")

        if op.action == "update":
            # not supported yet
            continue

        if op.action == "create" and car is not None:
            if not op.cid:
                continue

            create_info = {"uri": str(uri), "cid": str(op.cid), "author": commit.repo}

            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            record = models.get_or_create(record_raw_data, strict=False)
            if uri.collection == models.ids.AppBskyFeedPost and models.is_record_type(
                record,  # type: ignore
                models.ids.AppBskyFeedPost,
            ):
                operation_by_type["posts"]["created"].append(
                    {"record": record, **create_info}
                )

            # The following types of event don't need to be tracked by the feed right now, and are removed.
            # elif uri.collection == ids.AppBskyFeedLike and is_record_type(record, ids.AppBskyFeedLike):
            #     operation_by_type['likes']['created'].append({'record': record, **create_info})
            # elif uri.collection == ids.AppBskyFeedRepost and is_record_type(record, ids.AppBskyFeedRepost):
            #     operation_by_type['reposts']['created'].append({'record': record, **create_info})
            # elif uri.collection == ids.AppBskyGraphFollow and is_record_type(record, ids.AppBskyGraphFollow):
            #     operation_by_type['follows']['created'].append({'record': record, **create_info})

        if op.action == "delete":
            if uri.collection == models.ids.AppBskyFeedPost:
                operation_by_type["posts"]["deleted"].append({"uri": str(uri)})

            # The following types of event don't need to be tracked by the feed right now.
            # elif uri.collection == ids.AppBskyFeedLike:
            #     operation_by_type['likes']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyFeedRepost:
            #     operation_by_type['reposts']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyGraphFollow:
            #     operation_by_type['follows']['deleted'].append({'uri': str(uri)})

    return operation_by_type


def _get_required_ops(ops: dict):
    """Fetches the required operations from a _get_ops_by_type dict."""
    good_accounts = VALID_ACCOUNTS.get_accounts()
    existing_posts = EXISTING_POSTS.get_posts()

    # See how many posts need creating or deleting
    posts_to_create = [
        post for post in ops["posts"]["created"] if post["author"] in good_accounts
    ]
    posts_to_create = [
        post for post in posts_to_create if post["uri"] not in existing_posts
    ]
    posts_to_delete = [
        post["uri"] for post in ops["posts"]["deleted"] if post["uri"] in existing_posts
    ]

    return posts_to_create, posts_to_delete
