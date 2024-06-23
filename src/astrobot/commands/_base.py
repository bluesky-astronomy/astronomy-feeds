"""Base class for commands."""

from __future__ import annotations
from abc import ABC, abstractmethod
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from atproto import Client
from ..notifications import LikeNotification, ReplyNotification, MentionNotification


class Command(ABC):
    command = ""  # should be set by subclasses
    level = "user"  # user or moderator; user by default

    @staticmethod
    @abstractmethod
    def is_instance_of(
        notification: MentionNotification
    ) -> None | Command:
        """Check if a given string is a valid example of this command.

        If yes, then return an intialized version of this class with the command
        assigned.

        If no, return None.
        """
        pass

    @abstractmethod
    def execute(self, client: Client):
        """Executes the next step of a given command, or update to a command."""
        pass


class MultiStepCommand(Command):
    @staticmethod
    @abstractmethod
    def create_from_partial_step(
        notification: LikeNotification | ReplyNotification,
    ) -> MultiStepCommand | None:
        """Create a command from a notification that signals the start of a complete
        step. Returns None if the notification isn't a valid start of this command
        (e.g. if the author doesn't have the correct permissions.)
        """
        pass
