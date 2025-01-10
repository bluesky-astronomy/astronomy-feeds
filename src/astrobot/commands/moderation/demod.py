"""Remove a user as moderator."""

from __future__ import annotations

from atproto import Client
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification


class ModeratorDemodCommand(Command):
    command = "demod"
    level = 3

    def __init__(self, notification: MentionNotification):
        raise NotImplementedError()
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorDemodCommand:
        if notification.words[0] == ModeratorDemodCommand.command:
            return ModeratorDemodCommand(notification)
        # Todo should also check that the moderator has a higher mod level than the person that they're trying to ban

    def execute_good_permissions(self, client: Client):
        pass  # Todo
