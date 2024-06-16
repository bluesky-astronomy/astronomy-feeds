"""Standard functions for working with clients. Mostly just wraps atproto."""
from atproto import Client, Session, SessionEvent
import os


def get_client(
    handle_env_var: str, password_env_var: str, reuse_session: bool = True
) -> Client:
    """A standard function for getting a valid client - already logged in and 
    ready to go =)
    """       
    # Set up client and set it up to save its session incrementally
    client = Client()
    handle = _get_handle(handle_env_var)
    session_updater = BotSessionUpdater(handle)
    client.on_session_change(session_updater.on_session_change)

    # Login using previous session
    session = _get_session(handle)
    if session and reuse_session:
        # print("Reusing existing session")
        try:
            client.login(session_string=session)
            return client
        except Exception as e:
            print(f"Unable to log in with previous session! Reason: {e}")

    # We revert to password login if we can't find a session or if there was an issue
    # print("Logging in with password instead...")
    password = _get_password(password_env_var)
    client.login(handle, password)
    return client


def _get_session(handle: str) -> str | None:
    try:
        with open(f'{handle}.session') as f:
            return f.read()
    except FileNotFoundError:
        return None


def _get_handle(handle_env_var: str):
    """Checks and/or gets a handle for the client from an environment variable."""
    handle = os.getenv(handle_env_var, None)
    if handle is None:
        raise ValueError(
            f"You need to set the environment variable {handle_env_var} to your handle."
        )
    return handle


def _get_password(password_env_var: str):
    """Checks and/or gets a password for the client from an environment variable."""
    password = os.getenv(password_env_var, None)
    if password is None:
        raise ValueError(
            f"You need to set the environment variable {password_env_var} to your Bluesky app password."
        )
    return password


class BotSessionUpdater:
    def __init__(self, handle):
        """Simple class to save a bot's session to a file named {handle}.session."""
        self.handle = handle

    def on_session_change(self, event: SessionEvent, session: Session) -> None:
        """Callback to save session."""
        print('Session changed:', event, repr(session))
        if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
            # print('Saving changed session')
            self.save_session(session.export())

    def save_session(self, session_string: str) -> None:
        with open(f'{self.handle}.session', 'w') as f:
            f.write(session_string)
