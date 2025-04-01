import operator
from datetime import datetime
from functools import reduce
from typing import Optional, Final, Any

from peewee import fn

from astrofeed_lib import logger
from .accounts import CachedAccountQuery
from .database import Account, Post, BotActions, ActivityLog, NormalizedFeedStats

VALID_ACCOUNTS = CachedAccountQuery(flags=[Account.is_valid], query_interval=60)

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


def _select_activity_log_by_feed(feed: str, limit: int):
    return (
        ActivityLog.select(
            ActivityLog.id,
            ActivityLog.request_dt,
            ActivityLog.request_feed_uri,
            ActivityLog.request_is_scrolled,
            ActivityLog.request_limit,
        )
        .where(ActivityLog.request_feed_uri == feed)
        .order_by(ActivityLog.request_dt)
        .limit(limit)
    )


def _select_activity_log_by_date(date: str, limit: int):
    return (
        ActivityLog.select(
            ActivityLog.id,
            ActivityLog.request_dt,
            ActivityLog.request_feed_uri,
            ActivityLog.request_is_scrolled,
            ActivityLog.request_limit,
        )
        .where(
            fn.date_trunc("day", ActivityLog.request_dt)
            == datetime.strptime(date, "%Y-%m-%d")
        )
        .limit(limit)
    )


def _select_activity_log_by_did(did: str, limit: int):
    return (
        ActivityLog.select(
            ActivityLog.id,
            ActivityLog.request_dt,
            ActivityLog.request_feed_uri,
            ActivityLog.request_is_scrolled,
            ActivityLog.request_limit,
        )
        .where(ActivityLog.request_user_did == did)
        .order_by(ActivityLog.request_dt)
        .limit(limit)
    )


def _select_feed_stats(
    feed: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    day_of_week: int,
    group_by_feed: bool,
    group_by_year: bool,
    group_by_month: bool,
    group_by_day_of_week: bool,
):
    conditions: list = list()
    group_conditions: list = list()
    if feed != "all":
        conditions.append(NormalizedFeedStats.request_feed_uri == feed)
    else:
        conditions.append("1=1")
    if group_by_feed:
        group_conditions.append(NormalizedFeedStats.request_feed_uri)
    fields = [NormalizedFeedStats.request_feed_uri]

    if year != 0:
        conditions.append(NormalizedFeedStats.year == year)
        fields.append(NormalizedFeedStats.year)
    elif group_by_year:
        fields.append(NormalizedFeedStats.year)
        group_conditions.append(NormalizedFeedStats.year)
    if month != 0:
        conditions.append(NormalizedFeedStats.month == month)
        fields.append(NormalizedFeedStats.month)
    elif group_by_month:
        fields.append(NormalizedFeedStats.month)
        group_conditions.append(NormalizedFeedStats.month)
    if day != 0:
        conditions.append(NormalizedFeedStats.day == day)
        group_conditions.append(NormalizedFeedStats.day)
        fields.append(NormalizedFeedStats.day)
    if hour != -1:
        conditions.append(NormalizedFeedStats.hour == hour)
        group_conditions.append(NormalizedFeedStats.hour)
        fields.append(NormalizedFeedStats.hour)
    if day_of_week != -1:
        conditions.append(NormalizedFeedStats.day_of_week == day_of_week)
        fields.append(NormalizedFeedStats.day_of_week)
    elif group_by_day_of_week:
        fields.append(NormalizedFeedStats.day_of_week)
        group_conditions.append(NormalizedFeedStats.day_of_week)

    where_condition: str = reduce(operator.and_, conditions)

    fields.append(fn.count(1).alias("num_requests"))

    sql = NormalizedFeedStats.select(*fields).where(where_condition)
    sql = sql.group_by(*group_conditions)
    return sql


def _create_activity_log(logs: list[ActivityLog]) -> list[dict[str, Any]]:
    return [
        {
            "id": log.id,
            "request_dt": log.request_dt,
            "request_feed_uri": log.request_feed_uri,
            "request_is_scrolled": log.request_is_scrolled,
            "request_limit": log.request_limit,
        }
        for log in logs
    ]


def _create_feed_stats(stats: list[NormalizedFeedStats]) -> list[dict[str, Any]]:
    return [
        {
            "feed": stat.request_feed_uri,
            "year": stat.year,
            "month": stat.month,
            "day": stat.day,
            "hour": stat.hour,
            "day_of_week": stat.day_of_week,
            "num_requests": stat.num_requests,
        }
        for stat in stats
    ]


def _create_feed(posts):
    """Turns list of posts into a sorted"""
    return [{"post": post.uri} for post in posts]


def get_feed_logs_by_feed(feed: str, limit: int) -> dict:
    logs = _select_activity_log_by_feed(feed, limit)
    logger.info(f"Loaded logs from DB: {logs}")
    # Create the actual feed to send back to the user!
    log_details: list[dict[str, Any]] = _create_activity_log(logs)

    return {"logs": log_details}


def get_feed_logs_by_date(date: str, limit: int) -> dict:
    logs = _select_activity_log_by_date(date, limit)
    logger.info(f"Loaded logs from DB: {logs}")
    # Create the actual feed to send back to the user!
    log_details: list[dict[str, Any]] = _create_activity_log(logs)

    return {"logs": log_details}


def get_feed_logs_by_did(did: str, limit: int) -> dict:
    logs = _select_activity_log_by_did(did, limit)
    logger.info(f"Loaded logs from DB: {logs}")
    # Create the actual feed to send back to the user!
    log_details: list[dict[str, Any]] = _create_activity_log(logs)

    return {"logs": log_details}


def get_feed_stats(
    feed: str = "all",
    year: int = 0,
    month: int = 0,
    day: int = 0,
    hour: int = -1,
    day_of_week: int = -1,
    group_by_feed: bool = False,
    group_by_year: bool = False,
    group_by_month: bool = False,
    group_by_day_of_week: bool = False,
) -> dict:
    stats = _select_feed_stats(
        feed,
        year,
        month,
        day,
        hour,
        day_of_week,
        group_by_feed,
        group_by_year,
        group_by_month,
        group_by_day_of_week,
    )
    logger.debug(f"Loaded stats from DB with SQL: {stats.sql()}")
    feed_stats: list[dict[str, Any]] = _create_feed_stats(stats)
    logger.debug(f"Processed stats: {feed_stats}")
    return {"stats": feed_stats}


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
