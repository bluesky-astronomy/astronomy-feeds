"""Main loop for the astrobot!"""

import time
from .client import get_client
from .notifications import get_notifications, update_last_seen_time
from .commands import process_commands


print("Starting the astrobot!")

NOTIFICATION_SLEEP_TIME = 30
DESIRED_NOTIFICATIONS = {"like", "mention", "reply"}
HANDLE_ENV_VAR = "ASTROBOT_HANDLE"
PASSWORD_ENV_VAR = "ASTROBOT_PASSWORD"


while True:
    start_time = time.time()

    print("Getting client...")
    client = get_client(HANDLE_ENV_VAR, PASSWORD_ENV_VAR)

    print("Getting notifications...")
    notifications, notifications_seen_at = get_notifications(
        client, types=DESIRED_NOTIFICATIONS, fetch_all=True, unread_only=True
    )

    print(f"  found {len(notifications)} unread notifications!")
    if len(notifications) > 0:
        process_commands(notifications)

    update_last_seen_time(notifications_seen_at)

    # Sleep for the remainder of notification_sleep_time seconds
    print("All done! Sleeping...")
    sleep_time = NOTIFICATION_SLEEP_TIME - (time.time() - start_time)
    if sleep_time > 0:
        time.sleep(sleep_time)
