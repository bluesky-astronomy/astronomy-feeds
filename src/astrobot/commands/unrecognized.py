"""Tells the user that their command was unrecognized."""

from __future__ import annotations

from astrobot.notifications import MentionNotification
from ._base import Command
from ..post import send_post
from ..database import new_bot_action
from atproto import Client, models


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
    def is_instance_of(
        notification: MentionNotification
    ) -> None | UnrecognizedCommand:
        # For this class only, this method is not actually really intended... 
        # ... but we'll return it anyway! WE MUST OBEY THE INTERFACE (ABC) SPEC!!!!!!!!
        return UnrecognizedCommand(notification)

    def execute(self, client: Client):
        post_ref = models.create_strong_ref(self.notification.notification)
        send_post(client, unrecognized_command_text + self.extra, root_post=post_ref)

        new_bot_action(
            did=self.notification.author.did,
            type=self.command,
            stage="completed",
            parent_uri=self.notification.strong_ref.uri,
            parent_cid=self.notification.strong_ref.cid,
            latest_uri=self.notification.strong_ref.uri,
            latest_cid=self.notification.strong_ref.cid,
            complete=True,
        )
