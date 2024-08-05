"""Tools for handling and subclassing notifications."""

from datetime import datetime
from atproto import Client, models
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from astrobot.post import get_post
import warnings


ALLOWED_NOTIFICATION_TYPES = {"like", "repost", "follow", "mention", "reply", "quote"}


def get_notifications(
    client: Client,
    types: None | set[str] = None,
    limit: int | None = 50,
    seen_at: str | None = None,
    fetch_all: bool = True,
    unread_only: bool = True,
    reversed: bool = True,
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

    if reversed:
        all_notifications.reverse()

    return all_notifications, current_time


def update_last_seen_time(client: Client, current_time: str):
    client.app.bsky.notification.update_seen({"seen_at": current_time})


class BaseNotification:
    def match(self, botactions):
        """Matches a notification against a potential botaction."""
        for action in botactions:
            if (
                action.latest_uri == self.target.uri
                and action.latest_cid == self.target.cid
            ):
                self.action = action
                return True
        return False


class MentionNotification(BaseNotification):
    def __init__(self, notification: Notification):
        """A mention of the bot account."""
        from .config import HANDLE  # Imported here to prevent circular import

        self.author = notification.author
        self.text = notification.record.text
        self.parent_ref, self.root_ref = _get_strong_refs(notification)

        # Also setup all of the words in the command
        words = [w.lower() for w in self.text.split(" ")]
        mention_index = words.index("@" + HANDLE)
        self.words = words[mention_index + 1 :]

        self.notification = notification  # full notification, shouldn't need accessing

    def match(self, *args):
        raise NotImplementedError(
            "Mentions should never need matching, so this function is deactivated."
        )


class LikeNotification(BaseNotification):
    def __init__(self, notification: Notification):
        """A like from another user to a post made by the bot."""
        self.author = notification.author
        self.target = notification.record.subject
        self.parent_ref, self.root_ref = (
            models.create_strong_ref(self.target),
            None,  # Must be set with a later call to fetch_root_ref
        )
        self.action = None

        self.notification = notification  # full notification, shouldn't need accessing

    def fetch_root_ref(self, client: Client):
        """Fetches the root reference of the thread this post is in. By default,
        self.root_ref is None, as the notification does not include that information;
        this function performs a manual lookup on the network to get the root ref.
        """
        post_response = get_post(client, self.notification.record.subject)
        if not hasattr(post_response.value, "reply"):
            warnings.warn(
                "LikeNotification.fetch_root_ref: post that was liked is not actually "
                "a reply to anything, so unable to fetch root ref to post."
            )
            self.root_ref = self.parent_ref
            return
        self.root_ref = models.create_strong_ref(post_response.value.reply.root)


class ReplyNotification(BaseNotification):
    def __init__(self, notification: Notification):
        "A reply from another user to a post made by the bot."
        self.author = notification.author
        self.target = notification.record.reply.parent
        self.parent_ref, self.root_ref = _get_strong_refs(notification)
        self.action = None

        self.words = [w.lower() for w in self.text.split(" ")]

        self.notification = notification  # full notification, shouldn't need accessing


# atproto.xrpc_client.models.com.atproto.repo.strong_ref.Main
def _get_strong_refs(
    notification: MentionNotification | ReplyNotification,
) -> list[models.ComAtprotoRepoStrongRef.Main]:
    parent_ref = models.create_strong_ref(notification)
    if notification.record.reply is None:
        return parent_ref, parent_ref
    return parent_ref, models.create_strong_ref(notification.record.reply.root)


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
