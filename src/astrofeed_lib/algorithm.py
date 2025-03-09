from .database import Account, Post, BotActions, ActivityLog
from .accounts import CachedAccountQuery
from datetime import datetime
from typing import Optional, Final, Any
from astrofeed_lib import logger


VALID_ACCOUNTS = CachedAccountQuery(
    flags=[Account.is_valid], query_interval=60
)

CURSOR_END_OF_FEED: Final[str] = "eof"


def _select_posts(feed, limit):
    feed_boolean = getattr(Post, "feed_" + feed)
    return (
        Post.select(Post.indexed_at, Post.uri, Post.cid, Post.hidden)
        .join(Account, on=(Account.did == Post.author))
        .where(Account.is_valid, feed_boolean, ~Post.hidden)
        .order_by(Post.indexed_at.desc())
        .limit(limit)
    )


def _select_activity_log_by_feed(feed: str):
    return(ActivityLog.select(ActivityLog.id, ActivityLog.request_dt, ActivityLog.request_feed_uri
                              , ActivityLog.request_is_scrolled, ActivityLog.request_limit
                              , ActivityLog.request_user_did)
           .where(ActivityLog.request_feed_uri == feed)
           .order_by(ActivityLog.request_dt))


def _create_activity_log(logs: list[ActivityLog]) -> list[dict[str, Any]]:
    return [{"id": log.id, "request_dt": log.request_dt, "request_feed_uri": log.request_feed_uri
             , "request_is_scrolled": log.request_is_scrolled, "request_limit": log.request_limit
             , "request_user_did": log.request_user_did} for log in logs]


def _create_feed(posts):
    """Turns list of posts into a sorted"""
    return [{"post": post.uri} for post in posts]


def get_feed_logs(feed: str) -> dict:
    logs = _select_activity_log_by_feed(feed)
    logger.info(f"Loaded logs from DB: {logs}")
    # Create the actual feed to send back to the user!
    log_details: list[dict[str, Any]] = _create_activity_log(logs)

    return {"logs": log_details}


def _handle_cursor(cursor, posts):
    """Handles cursor operations if one is included in the request"""
    timestamp, cid = unpack_cursor(cursor)
    posts = posts.where(
        ((Post.indexed_at == timestamp) & (Post.cid < cid))
        | (Post.indexed_at < timestamp)  # type: ignore
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

    # Hard-coded exceptions
    if feed == "signup":
        return get_posts_signup_feed(cursor, limit)

    # Setup a query that's only for valid accounts
    # valid_dids = VALID_ACCOUNTS.get_accounts()
    posts = _select_posts(feed, limit)

    # If the client specified a cursor, limit the posts to within some time range
    if cursor:
        posts = _handle_cursor(cursor, posts)

    # Create the actual feed to send back to the user!
    post_uris = _create_feed(posts)
    cursor = _move_cursor_to_last_post(posts)

    return {"cursor": cursor, "feed": post_uris}


def get_posts_signup_feed(cursor: Optional[str], limit: int) -> dict:
    """A special-case feed that contains all current signup attempts on the Astronomy
    feed. Really really annoyingly, it's difficult to just use the same feed methods as
    it includes multiple different column names & Peewee's OOP approach would make this
    hellish.
    """
    # TODO: refactor this into separate methods, or somehow make existing ones more compatible
    # Initial query
    posts = (
        BotActions.select(
            BotActions.indexed_at, BotActions.latest_uri, BotActions.latest_cid
        )
        .where(
            BotActions.complete == False,  # noqa: E712
            BotActions.type == "signup",
            BotActions.stage == "get_moderator",
        )
        .order_by(BotActions.indexed_at.desc())
        .limit(limit)
    )

    # Handle cursor
    if cursor:
        timestamp, cid = unpack_cursor(cursor)
        posts = posts.where(
            ((BotActions.indexed_at == timestamp) & (BotActions.latest_cid < cid))  # type: ignore
            | (BotActions.indexed_at < timestamp)  # type: ignore
        )

    # Extract URIs
    post_uris = [{"post": post.latest_uri} for post in posts]

    # Create cursor for feed
    last_post = posts[-1] if posts else None
    cursor = CURSOR_END_OF_FEED
    if last_post:
        cursor = create_cursor(last_post.indexed_at.timestamp(), last_post.latest_cid)

    return {"cursor": cursor, "feed": post_uris}
