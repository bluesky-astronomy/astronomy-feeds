"""Logic for how commits are filtered."""

import logging
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState, db, Post
from astrofeed_lib.feeds import post_in_feeds
from atproto import CAR, AtUri, parse_subscribe_repos_message
from atproto import models
from atproto.exceptions import ModelError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _process_commit(
    message, cursor, valid_accounts, existing_posts, update_cursor_in_database=True
):
    """Attempt to process a single commit. Returns a list of any new posts to add."""
    # # Skip any commits that do not pass this model (which can occur sometimes)
    # try:
    #     commit = parse_subscribe_repos_message(message)
    # except ModelError:
    #     logger.exception("Unable to process a commit due to validation issue")
    #     return []

    # # Final check that this is in fact a commit, and not e.g. a handle change
    # if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
    #     return []
    # TODO: remove after doing checking of this in the async bit
    commit = message

    new_posts = apply_commit(commit, valid_accounts, existing_posts)

    # Update stored state every ~100 posts
    if commit['cursor'] % 100 == 0:
        cursor.value = commit['cursor']
        # if commit['cursor'] % 100 == 0:
        if update_cursor_in_database:
            db.connect(reuse_if_open=True)
            SubscriptionState.update(cursor=commit['cursor']).where(
                SubscriptionState.service == SERVICE_DID
            ).execute()
            db.close()
        else:
            logger.info(f"Cursor: {commit['cursor']}")

    # Notify the manager process of either a) a new post, or b) that we're done with
    # this commit
    return new_posts


def apply_commit(
    commit: dict,  #models.ComAtprotoSyncSubscribeRepos.Commit,
    valid_accounts: set,
    existing_posts: set,
) -> list:
    """Applies the operations in a commit based on which ones are necessary to process."""
    # ops = _get_ops_by_type(commit)
    # cursor = commit.seq
    # TODO: REMOVE COMMENTED OUT BIT
    ops = commit
    cursor = ops['cursor']

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
        post["uri"] for post in ops["posts"]["deleted"] if post["uri"] in existing_posts
    ]

    # Perform database operations
    if posts_to_delete or posts_to_create:
        db.connect(reuse_if_open=True)

        if posts_to_delete:
            Post.delete().where(Post.uri.in_(posts_to_delete))
            logger.info(f"Deleted posts: {len(posts_to_delete)} (cursor={cursor})")

        if posts_to_create:
            with db.atomic():
                for post_dict in posts_to_create:
                    Post.create(**post_dict)
            feed_counts_string = ", ".join(
                [f"{key[5:]}-{feed_counts[key]}" for key in feed_counts]
            )
            logger.info(f"Added posts: {feed_counts_string} (cursor={cursor})")

        db.close()

    if not posts_to_create:
        return []
    return [post["uri"] for post in posts_to_create]


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> dict:  # noqa: C901
    """Sorts all commits/operations by type into a convenient to process dictionary."""
    operation_by_type = {
        "posts": {"created": [], "deleted": []},
        "reposts": {"created": [], "deleted": []},
        "likes": {"created": [], "deleted": []},
        "follows": {"created": [], "deleted": []},
        "has_ops": False,
        "cursor": commit.seq
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
                operation_by_type["has_ops"] = True

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
                operation_by_type["has_ops"] = True

            # The following types of event don't need to be tracked by the feed right now.
            # elif uri.collection == ids.AppBskyFeedLike:
            #     operation_by_type['likes']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyFeedRepost:
            #     operation_by_type['reposts']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyGraphFollow:
            #     operation_by_type['follows']['deleted'].append({'uri': str(uri)})

    return operation_by_type
