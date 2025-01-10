"""Standard functions for working with Bluesky clients."""

from atproto import Client, Session, SessionEvent


def get_client(handle: str, password: str, reuse_session: bool = True) -> Client:
    """A standard function for getting a valid client - already logged in and
    ready to go =)
    """
    # Set up client and set it up to save its session incrementally
    client = Client()
    session_updater = BotSessionUpdater(handle)
    client.on_session_change(session_updater.on_session_change)

    # Login using previous session
    session = _get_session(handle)
    if session and reuse_session:
        try:
            client.login(session_string=session)
            return client
        except Exception as e:
            print(f"Unable to log in with previous session! Reason: {e}")

    # We revert to password login if we can't find a session or if there was an issue
    client.login(handle, password)
    return client


def _get_session(handle: str) -> str | None:
    try:
        with open(f"{handle}.session") as f:
            return f.read()
    except FileNotFoundError:
        return None


class BotSessionUpdater:
    def __init__(self, handle):
        """Simple class to save a bot's session to a file named {handle}.session."""
        self.handle = handle

    def on_session_change(self, event: SessionEvent, session: Session) -> None:
        """Callback to save session."""
        print("Session changed:", event, repr(session))
        if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
            self.save_session(session.export())

    def save_session(self, session_string: str) -> None:
        with open(f"{self.handle}.session", "w") as f:
            f.write(session_string)
