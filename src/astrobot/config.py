"""Various configuration-related things about the bot."""

import os
from .commands import CommandRegistry
from .commands.joke import JokeCommand
from .commands.signup import SignupCommand


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


# Typical config options
NOTIFICATION_SLEEP_TIME = 10
DESIRED_NOTIFICATIONS = {"like", "mention", "reply"}
HANDLE = _get_handle("ASTROBOT_HANDLE")  # Name of handle environment variable
PASSWORD = _get_password("ASTROBOT_PASSWORD")  # Name of password environment variable

# Setup command registry
COMMAND_REGISTRY = CommandRegistry()
COMMAND_REGISTRY.register_commands([JokeCommand, SignupCommand])
