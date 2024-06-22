"""Initial entrypoints for processing commands to the bot."""

from atproto_client.models.app.bsky.notification.list_notifications import Notification
from ..moderation import get_moderators
from atproto import Client
from ..config import COMMAND_REGISTRY


def process_commands(client: Client, notifications: list[Notification], handle: str):
    print("Processing notifications...")

    # moderators = get_moderators()

    # Get all mentions and try to see if any are new commands
    new_commands = _look_for_new_commands(notifications, handle)
    updated_commands = _look_for_updates_to_multistep_commands(notifications)

    # todo: still need to execute them
    # todo: would also be nice to get diagnostics BEFORE things execute!


def _look_for_new_commands(notifications: list[Notification], handle: str):
    """Looks for mentions that contain a command for the bot. Returns a list of commands
    to execute.
    """
    mentions = [n for n in notifications if n.reason == "mention"]

    if not mentions:
        return []

    return [COMMAND_REGISTRY.get_matching_command(m, handle) for m in mentions]


def _look_for_updates_to_multistep_commands(notifications: list[Notification]):
    # todo: pre-filter notifications for only those that act on a 'latest post'
    pass
