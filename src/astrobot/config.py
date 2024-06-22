"""Various configuration-related things about the bot."""
from .commands import CommandRegistry
from .commands.joke import JokeCommand

# Typical config options
NOTIFICATION_SLEEP_TIME = 30
DESIRED_NOTIFICATIONS = {"like", "mention", "reply"}
HANDLE_ENV_VAR = "ASTROBOT_HANDLE"
PASSWORD_ENV_VAR = "ASTROBOT_PASSWORD"

# Setup command registry
COMMAND_REGISTRY = CommandRegistry()
COMMAND_REGISTRY.register_command(JokeCommand)