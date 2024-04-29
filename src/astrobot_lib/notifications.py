from time import sleep

from . import client

# how often we should check for new notifications
FETCH_NOTIFICATIONS_DELAY_SEC = 3


def get_notifications() -> None:
    client = client.get_client(handle_env_var='BSKY_USER', password_env_var='BSKY_PASS')

    # fetch new notifications
    while True:
        # save the time in UTC when we fetch notifications
        last_seen_at = client.get_current_time_iso()

        response = client.app.bsky.notification.list_notifications()
        for notification in response.notifications:
            if not notification.is_read:
                print(f'Got new notification! Type: {notification.reason}; record: {notification.record}')
                if notification.reason == 'mention':
                    print('Someone mentioned your post!')

        # mark notifications as processed (isRead=True)
        #client.app.bsky.notification.update_seen({'seen_at': last_seen_at})
        print('Successfully process notification. Last seen at:', last_seen_at)

        #sleep(FETCH_NOTIFICATIONS_DELAY_SEC)


if __name__ == '__main__':
    get_notifications()