from .database import Account, Post
from .accounts import CachedAccountQuery
from datetime import datetime
from typing import Optional


VALID_ACCOUNTS = CachedAccountQuery(
    with_database_closing=False, flags=[Account.is_valid], query_interval=60
)

CURSOR_END_OF_FEED = "eof"


def _select_posts(feed, valid_dids, limit):
    feed_boolean = getattr(Post, "feed_" + feed)
    return (
        Post.select()
        .where(Post.author.in_(valid_dids), feed_boolean)
        .order_by(Post.indexed_at.desc())
        .limit(limit)
    )


def _create_feed(posts):
    """Turns list of posts into a sorted"""
    return [{"post": post.uri} for post in posts]


def _handle_cursor(cursor, posts):
    """Handles cursor operations if one is included in the request"""
    timestamp, cid = unpack_cursor(cursor)
    posts = posts.where(
        ((Post.indexed_at == timestamp) & (Post.cid < cid))
        | (Post.indexed_at < timestamp)
    )
    return posts


def _move_cursor_to_last_post(posts):
    last_post = posts[-1] if posts else None
    if last_post:
        return create_cursor(last_post.indexed_at.timestamp(), last_post.cid)
    return CURSOR_END_OF_FEED


def unpack_cursor(cursor):
    """Converts a feed cursor into a timestamp and a cid for a post."""
    cursor_parts = cursor.split("::")
    if len(cursor_parts) != 2:
        raise ValueError("Malformed cursor")
    indexed_at, cid = cursor_parts
    timestamp = datetime.fromtimestamp(int(indexed_at) / 1000)
    return timestamp, cid


def create_cursor(timestamp, cid):
    """Converts a timestamp and cid for a post into a feed cursor."""
    return f"{int(timestamp * 1000)}::{cid}"


def get_posts(feed: str, cursor: Optional[str], limit: int) -> dict:
    """Gets posts for a given feed!"""
    # Early return if the cursor is just the end of feed indicator
    if cursor == CURSOR_END_OF_FEED:
        return {"cursor": CURSOR_END_OF_FEED, "feed": []}

    # Setup a query that's only for valid accounts
    valid_dids = VALID_ACCOUNTS.get_accounts()
    posts = _select_posts(feed, valid_dids, limit)

    # If the client specified a cursor, limit the posts to within some time range
    if cursor:
        posts = _handle_cursor(cursor, posts)

    # Create the actual feed to send back to the user!
    post_uris = _create_feed(posts)
    cursor = _move_cursor_to_last_post(posts)

    return {"cursor": cursor, "feed": post_uris}
