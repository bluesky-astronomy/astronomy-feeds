"""Initial entrypoints for processing commands to the bot."""

from atproto_client.models.app.bsky.notification.list_notifications import Notification
from atproto import Client
from .config import COMMAND_REGISTRY
from .database import get_outstanding_bot_actions, teardown_connection, get_database
from .notifications import LikeNotification, ReplyNotification, MentionNotification
from icecream import ic

# set up icecream
ic.configureOutput(includeContext=True)

def process_commands(client: Client, notifications: list[Notification]):
    ic("Processing notifications...")
    # Get all mentions and try to see if any are new commands
    new_commands = _look_for_new_commands(notifications)
    updated_commands = _look_for_updates_to_multistep_commands(notifications)

    ic(f"-> found {len(new_commands)} new commands")
    if new_commands:
        to_print = ", ".join(
            [f"{c.notification.author.handle}: {c.command}" for c in new_commands]
        )
        ic(f"   with types: {to_print}")
    ic(f"-> found {len(updated_commands)} valid updates to commands")
    if updated_commands:
        to_print = ",".join(
            [f"{c.notification.author.handle}: {c.command}" for c in updated_commands]
        )
        ic(f"   with types: {to_print}")

    ic("Executing...")
    for command in new_commands + updated_commands:
        ic(
            f"-> running command {command.command} acting on {command.notification.author.handle}"
        )
        command.execute(client)


def _look_for_new_commands(
    notifications: list[Notification],
) -> list:
    """Looks for mentions that contain a command for the bot. Returns a list of commands
    to execute.
    """
    mentions = [MentionNotification(n) for n in notifications if n.reason == "mention"]

    if not mentions:
        return []

    return [COMMAND_REGISTRY.get_matching_command(m) for m in mentions]


def _look_for_updates_to_multistep_commands(
    notifications: list[Notification],
) -> list:
    """Matches notifications with ongoing botactions."""
    # Filter to just notifications that are likes, replies, or mentions with a reply
    good_notifications = extract_likes_and_replies(notifications)
    if len(good_notifications) == 0:
        return []

    # Get all actions that could be associated with these notifications
    uris = [n.target.uri for n in good_notifications]
    actions = get_outstanding_bot_actions(uris)
    if len(actions) == 0:
        teardown_connection(get_database())
        return []

    # Limit to just those that match an action
    good_notifications = [n for n in good_notifications if n.match(actions)]
    if len(good_notifications) == 0:
        teardown_connection(get_database())
        return []

    # FINALLY, convert all of these matched notifications into commands
    commands = []
    for notification in good_notifications:
        command = COMMAND_REGISTRY.get_matching_multistep_command(notification)
        if command is not None:
            commands.append(command)
    teardown_connection(get_database())
    return commands


def extract_likes_and_replies(
    notifications: list[Notification],
) -> list[LikeNotification, ReplyNotification]:
    good_notifications = []
    for notification in notifications:
        if notification.reason == "like":
            good_notifications.append(LikeNotification(notification))

        elif notification.reason == "reply":
            good_notifications.append(ReplyNotification(notification))

        # Optional: we can also check mentions for information, as a mention may also be
        # a reply against the bot itself.
        elif notification.reason == "mention":
            if hasattr(notification.record, "reply"):
                if notification.record.reply is not None:
                    # Todo could also pre-filter for replies against the bot itself (would need DID)
                    good_notifications.append(ReplyNotification(notification))

    return good_notifications
