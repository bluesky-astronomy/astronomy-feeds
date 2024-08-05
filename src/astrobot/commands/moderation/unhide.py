"""Unhide a post from the feeds that was previously hidden."""

from __future__ import annotations

from atproto import Client
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification


class ModeratorUnhideCommand(Command):
    command = "unhide"
    level = 2

    def __init__(self, notification: MentionNotification):
        raise NotImplementedError()
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorUnhideCommand:
        if notification.words[0] == ModeratorUnhideCommand.command:
            return ModeratorUnhideCommand(notification)

    def execute_good_permissions(self, client: Client):
        pass  # Todo
