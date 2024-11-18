"""Test of how to fetch details of content that's gone stale."""

from astrobot.client import get_client
from astrobot.notifications import (
    LikeNotification,
    ReplyNotification,
    get_notifications_from_stale_commands,
)
from astrobot.process import process_commands


client = get_client()

notifications = get_notifications_from_stale_commands(
    client, commands_to_check=["signup"]
)


for notification in notifications:
    print("NOTIFICATION: ------------------------------")
    print(notification.indexed_at, notification.reason)

    # Check that it can turn into an astrobot notification ok
    if notification.reason == "like":
        final_not = LikeNotification(notification)
        final_not.fetch_root_ref(client)

    elif notification.reason == "reply":
        final_not = ReplyNotification(notification)


print("Attempting to process commands...")
if len(notifications) > 0:
    process_commands(client, notifications)
