"""Standard functions for working with clients. Mostly just wraps atproto."""
from atproto import AsyncClient
import os


def get_client(
    handle: str, password: str | None = None, password_env_var: str | None = None
) -> AsyncClient:
    """A standard function for getting a valid Async client."""
    if password is None and password_env_var is None:
        raise ValueError(
            "Must specify a password or an environment variable to get one from!"
        )
    if password is None:
        password = os.getenv(password_env_var, None)
        if password is None:
            raise ValueError(
                f"You need to set the environment variable {password_env_var} to your Bluesky app password."
            )

    client = AsyncClient()
    client.login(handle, password)  # Todo: support saved session instead

    return client
