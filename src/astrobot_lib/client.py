"""Standard functions for working with clients. Mostly just wraps atproto."""
from atproto import AsyncClient
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


def get_client(
    handle: str, password: str | None = None, password_env_var: str | None = None
) -> AsyncClient:
    """A standard function for getting a valid Async client - already logged in and ready to go =)"""
    if not isinstance(handle, str):
        raise ValueError("handle must be a string.")
    password = _get_password(password, password_env_var)
    client = AsyncClient()
    client.login(handle, password)  # Todo: support saved session instead
    return client
