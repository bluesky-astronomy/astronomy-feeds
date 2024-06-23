"""Tells the user that their command was unrecognized."""

from __future__ import annotations

from astrobot.notifications import MentionNotification
from ._base import Command
from ..post import send_post
from ..database import new_bot_action
from atproto import Client


unrecognized_command_text = "Sorry, but I don't recognize that command."


class UnrecognizedCommand(Command):
    command = "unrecognized"

    def __init__(self, notification: MentionNotification, extra=""):
        self.notification = notification
        self.extra = extra

        # In general, we probably always want this logged for informational purposes
        print(
            f"UNRECOGNIZED COMMAND: failed to find command in post from "
            f"{notification.author.handle} with text {notification.text}"
        )

    @staticmethod
    def is_instance_of(notification: MentionNotification) -> None | UnrecognizedCommand:
        # For this class only, this method is not actually really intended...
        # ... but we'll return it anyway! WE MUST OBEY THE INTERFACE (ABC) SPEC!!!!!!!!
        return UnrecognizedCommand(notification)

    def execute(self, client: Client):
        send_post(
            client,
            unrecognized_command_text + self.extra,
            root_post=self.notification.root_ref,
            parent_post=self.notification.parent_ref,
        )

        new_bot_action(self)
