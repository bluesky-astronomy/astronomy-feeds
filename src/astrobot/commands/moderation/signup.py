"""Manually sign up a user to the feeds."""

from __future__ import annotations

from atproto import Client
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification


class ModeratorSignupCommand(Command):
    command = "manualsignup"
    level = 1

    def __init__(self, notification: MentionNotification):
        raise NotImplementedError()
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorSignupCommand:
        if notification.words[0] == ModeratorSignupCommand.command:
            return ModeratorSignupCommand(notification)

    def execute_good_permissions(self, client: Client):
        pass  # Todo
