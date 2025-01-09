"""Ban a user from the feeds."""

from __future__ import annotations

from atproto import Client
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification


class ModeratorBanCommand(Command):
    command = "ban"
    level = 3

    def __init__(self, notification: MentionNotification):
        raise NotImplementedError()
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorBanCommand:
        if notification.words[0] == ModeratorBanCommand.command:
            return ModeratorBanCommand(notification)

    def execute_good_permissions(self, client: Client):
        pass  # Todo
