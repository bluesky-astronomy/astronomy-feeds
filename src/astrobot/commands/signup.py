"""Signs a user up to the feed."""

from __future__ import annotations

from astrobot.database import new_bot_action, update_bot_action
from ._base import MultiStepCommand
from ..post import send_post, send_thread
from atproto import Client
from ..notifications import MentionNotification, LikeNotification, ReplyNotification
from ..moderation import MODERATORS
from typing import Callable


RULES_POSTS = [
    "Thank you for your interest in signing up to the Astronomy feeds! There are a few steps to this that I'll guide you through.\n\nThis bot is experimental; if you have any issues, please tag (at)emily.space, the bot's maintainer.",
    "The astronomy feeds require validation to sign up to, and we want to keep it a safe and accurate source of information. You'll need to agree to the following rules to post to it:",
    "1. You must be a professional, amateur, aspiring, or in-training astronomer to join. It's also absolutely ok if you left the field but still want to sign up - we want to be an inclusive online space.\n\n2. No misinformation.",
    "\n\n5. No spamming.\n\n6. No impersonation.\n\n7. If you post content that is not your own, you MUST credit the original author.",
    "If you agree to the above rules, please reply to this post with a 'yes'."
]


def _execute_rules_sent(command: SignupCommand, client: Client):
    send_thread(client, RULES_POSTS)
    new_bot_action(command, stage="rules_sent")


def _execute_get_description(command: SignupCommand, client: Client):
    pass


def _execute_get_moderator(command: SignupCommand, client: Client):
    pass


def _execute_complete(command: SignupCommand, client: Client):
    pass


class SignupCommand(MultiStepCommand):
    """Sign up a user to the feeds.

    This command is multi-step, and has the following steps:
    'rules_sent':
    USER: mention with "@bot.astronomy.blue signup"
    BOT: send rules

    'get_description':
    USER: reply "yes"
    BOT: ask user to reply with why they want to join the feed

    'get_moderator':
    USER: reply with answer
    BOT: reply thanks and tag moderators

    'complete':
    MODERATOR: like bot last post
    BOT: tell user they are signed up, perform db actions, send further instructions
    """

    command = "signup"

    def __init__(
        self,
        notification: MentionNotification,
        execute_method: Callable[[SignupCommand, Client], None] = _execute_rules_sent,
    ):
        self.notification = notification
        self.execute_command = execute_method

    @staticmethod
    def is_instance_of(notification: MentionNotification) -> None | SignupCommand:
        if notification.words[0] == SignupCommand.command:
            return SignupCommand(notification)

        # Additional spellings
        if notification.words[0] == "sign" and notification.words[1] == "up":
            return SignupCommand(notification)
        if notification.words[0] == "sign-up":
            return SignupCommand(notification)

    @staticmethod
    def create_from_partial_step(
        notification: LikeNotification | ReplyNotification,
    ) -> MultiStepCommand | None:
        """Create a command from a notification that signals the start of a complete
        step. Returns None if the notification isn't a valid start of this command
        (e.g. if the author doesn't have the correct permissions.)
        """
        stage = notification.action.stage
        is_like = isinstance(notification, LikeNotification)
        is_reply = isinstance(notification, ReplyNotification)
        is_author = notification.author.did == notification.action.did
        is_moderator = notification.author.did in MODERATORS.get_accounts()

        # Check to see if user has accepted the rules
        if stage == "rules_sent" and is_author and is_reply:
            return SignupCommand(notification, _execute_get_description)
        
        # Check to see if user replied with a post
        if stage == "get_description" and is_author and is_reply:
            return SignupCommand(notification, _execute_get_moderator)

        # Check to see if moderator liked the bot's previous post
        if stage == "get_moderator" and is_moderator and is_like:
            return SignupCommand(notification, _execute_complete)

        print(
            f"Attempted to match a notification to command {MultiStepCommand.command}, "
            f"but notification is not a valid match. Type: {notification.__class__}; "
            f"author: {notification.author.handle}"
        )
        return None

    def execute(self, client: Client):
        """Execute the command. Defined in __init__."""
        return self.execute_command(self, client)
