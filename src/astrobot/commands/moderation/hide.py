"""Hide a post from the feeds."""

from __future__ import annotations

from atproto import Client
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification


class ModeratorHideCommand(Command):
    command = "hide"
    level = 2

    def __init__(self, notification: MentionNotification):
        raise NotImplementedError()
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorHideCommand:
        if notification.words[0] == ModeratorHideCommand.command:
            return ModeratorHideCommand(notification)

    def execute_good_permissions(self, client: Client):
        pass  # Todo
