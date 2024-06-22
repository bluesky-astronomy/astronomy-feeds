"""Tells the user that their command was unrecognized."""

from __future__ import annotations
from ._base import Command
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from ..post import send_post
from atproto import Client, models


unrecognized_command_text = "Sorry, but I don't recognize that command."


class UnrecognizedCommand(Command):
    command = ""

    def __init__(self, notification: Notification, extra=""):
        self.notification = notification
        self.extra = extra

        # In general, we probably always want this logged for informational purposes
        print(
            f"UNRECOGNIZED COMMAND: failed to find command in post from "
            f"{notification.author.handle} with text {notification.record.text}"
        )

    @staticmethod
    def is_instance_of(
        words: list[str], notification: Notification
    ) -> None | UnrecognizedCommand:
        # For this class only, this method is not actually really intended... 
        # ... but we'll return it anyway! WE MUST OBEY THE INTERFACE (ABC) SPEC!!!!!!!!
        return UnrecognizedCommand(notification)

    def execute(self, client: Client):
        post_ref = models.create_strong_ref(self.notification)
        send_post(client, unrecognized_command_text + self.extra, root_post=post_ref)
