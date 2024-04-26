"""Standard functions for working with clients. Mostly just wraps atproto."""
from atproto import AsyncClient, Client
import os


def _get_password(password: str | None = None, password_env_var: str | None = None):
    """Checks and/or gets a password for the client from an environment variable."""
    # Early return if password already set
    if password is not None:
        if not isinstance(password, str):
            raise ValueError("password must be a string")
        return password

    # See if the user at least set password_env_var
    if password_env_var is None:
        raise ValueError(
            "You must specify a password or an environment variable to get one from!"
        )

    # Try to get password from environment instead
    password = os.getenv(password_env_var, None)
    if password is None:
        raise ValueError(
            f"You need to set the environment variable {password_env_var} to your Bluesky app password."
        )
    return password

def _get_handle(handle_env_var: str | None = None):
    """Checks and/or gets a handle for the client from an environment variable."""

    # See if the user at least set handle_env_var
    if handle_env_var is None:
        raise ValueError(
            "You must specify a handle or an environment variable to get one from!"
        )

    # Try to get handle from environment instead
    handle = os.getenv(handle_env_var, None)
    if handle is None:
        raise ValueError(
            f"You need to set the environment variable {handle_env_var} to your handle."
        )
    return handle


def get_client(
    handle_env_var: str, password: str | None = None, password_env_var: str | None = None
) -> Client:
    """A standard function for getting a valid Async client - already logged in and ready to go =)"""
    if not isinstance(handle_env_var, str):
        raise ValueError("handle must be a string.")
    password = _get_password(password, password_env_var)
    handle = _get_handle(handle_env_var)
    client = Client()
    print(handle, password)
    client.login(handle, password)  # Todo: support saved session instead
    return client


FETCH_NOTIFICATIONS_DELAY_SEC = 3


def get_notifications() -> None:
    client = get_client(handle_env_var='BSKY_USER', password_env_var='BSKY_PASS')

    # fetch new notifications
    while True:
        # save the time in UTC when we fetch notifications
        last_seen_at = client.get_current_time_iso()

        response = client.app.bsky.notification.list_notifications()
        for notification in response.notifications:

            # notifications.response contains a lot of info about the post
            # notifications.author contains a lot of info about the author
            
            if not notification.is_read:
                if notification.reason == 'mention':
                    text = notification.record.text
                    if ('sign up' in text) or ('sign-up' in text) or ('signup' in text):
                        print(f'User {notification.author.handle} wants to sign up.')
                        print(f'User name: {notification.author.display_name}')
                        print(f'User DID: {notification.author.did}')
                        print(f'User description: {notification.author.description}')
                
        # mark notifications as processed (isRead=True)
        client.app.bsky.notification.update_seen({'seen_at': last_seen_at})
        print('Successfully process notification. Last seen at:', last_seen_at)

        sleep(FETCH_NOTIFICATIONS_DELAY_SEC)
