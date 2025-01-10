"""Main loop for the astrobot!"""

import time
from .client import get_client
from .notifications import (
    get_notifications,
    update_last_seen_time,
    get_notifications_from_stale_commands,
)
from .process import process_commands
from .config import (
    DESIRED_NOTIFICATIONS,
    NOTIFICATION_SLEEP_TIME,
    COMMAND_REGISTRY,
    MAX_COMMAND_AGE,
    STALE_COMMAND_CHECK_INTERVAL
)


def run_bot():
    print("Starting the astrobot!")
    i = 0
    while True:
        start_time = time.time()

        print("Getting client...")
        client = get_client()

        print("Getting notifications...")
        notifications, notifications_seen_at = get_notifications(
            client, types=DESIRED_NOTIFICATIONS, fetch_all=True, unread_only=True
        )

        print(f"-> found {len(notifications)} unread notifications!")
        if len(notifications) > 0:
            process_commands(client, notifications)

        update_last_seen_time(client, notifications_seen_at)

        # Optionally also check for any stale commands
        # TODO: get some kind of better criteria for how often to do this, ideally based on aiming to check for staleness once every ~3 hours
        if i % STALE_COMMAND_CHECK_INTERVAL == 0:
            print("Performing check for stale commands...")
            notifications = get_notifications_from_stale_commands(
                client, COMMAND_REGISTRY.list_multistep_commands(), age=MAX_COMMAND_AGE
            )
            print(f"-> found {len(notifications)} potential stale notifications!")
            if len(notifications) > 0:
                process_commands(client, notifications)

        # Sleep for the remainder of notification_sleep_time seconds
        print("All done! Sleeping...")
        sleep_time = NOTIFICATION_SLEEP_TIME - (time.time() - start_time)
        if sleep_time > 0:
            time.sleep(sleep_time)

        i += 1


if __name__ == "__main__":
    run_bot()
