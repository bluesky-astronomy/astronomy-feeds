from datetime import datetime
from atproto import Client


ALLOWED_NOTIFICATION_TYPES = {"like", "repost", "follow", "mention", "reply", "quote"}


def get_notifications(
    client: Client,
    types: None | set[str] = None,
    limit: int | None = 50,
    seen_at: str | None = None,
    fetch_all: bool = True,
    unread_only: bool = True,
) -> None:
    """Gets all current notifications attached to a client."""
    current_time = client.get_current_time_iso()

    # Fetch all notifications
    responses, last_seen_time = _fetch_notifications_recursive(
        client, limit, seen_at, fetch_all
    )

    all_notifications = []
    for response in responses:
        all_notifications.extend(response.notifications)

    # Filter notifications to only desired ones
    if types:
        all_notifications = [n for n in all_notifications if n.reason in types]

    if unread_only:
        all_notifications = [
            n
            for n in all_notifications
            if iso_time_to_datetime(n.indexed_at) > last_seen_time
        ]

    return all_notifications, current_time


def update_last_seen_time(client: Client, current_time: str):
    client.app.bsky.notification.update_seen({"seen_at": current_time})


def _fetch_notifications_recursive(
    client: Client, limit: int = 50, seen_at: None | str = None, fetch_all: bool = True
):
    responses = []
    cursor = None
    while True:
        responses.append(
            client.app.bsky.notification.list_notifications(
                params=dict(limit=limit, seen_at=seen_at, cursor=cursor)
            )
        )
        last_seen_time = iso_time_to_datetime(responses[-1].seen_at)

        if not fetch_all or responses[-1].cursor is None:
            return responses, last_seen_time

        cursor = responses[-1].cursor
        if iso_time_to_datetime(cursor) < last_seen_time:
            return responses, last_seen_time


def datetime_to_iso_time(date: datetime):
    return date.isoformat()


def iso_time_to_datetime(date: str):
    return datetime.fromisoformat(date)
