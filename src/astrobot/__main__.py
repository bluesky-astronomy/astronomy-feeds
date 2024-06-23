"""Main loop for the astrobot!"""

import time
from .client import get_client
from .notifications import get_notifications, update_last_seen_time
from .process import process_commands
from .config import (
    DESIRED_NOTIFICATIONS,
    NOTIFICATION_SLEEP_TIME,
)


def run_bot():
    print("Starting the astrobot!")
    while True:
        start_time = time.time()

        print("Getting client...")
        client = get_client()

        print("Getting notifications...")
        notifications, notifications_seen_at = get_notifications(
            client, types=DESIRED_NOTIFICATIONS, fetch_all=True, unread_only=True
        )

        print(notifications)

        print(f"-> found {len(notifications)} unread notifications!")
        if len(notifications) > 0:
            process_commands(client, notifications)

        update_last_seen_time(client, notifications_seen_at)
        break

        # Sleep for the remainder of notification_sleep_time seconds
        print("All done! Sleeping...")
        sleep_time = NOTIFICATION_SLEEP_TIME - (time.time() - start_time)
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    run_bot()
