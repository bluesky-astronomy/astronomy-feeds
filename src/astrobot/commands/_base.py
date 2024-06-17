"""Base class for commands."""

from __future__ import annotations
from abc import ABC, abstractmethod
from atproto_client.models.app.bsky.notification.list_notifications import Notification


class Command(ABC):
    command = ""  # should be set by subclasses
    level = "user"  # user or moderator; user by default

    @staticmethod
    @abstractmethod
    def is_instance_of(
        command: list[str], notification: Notification
    ) -> None | Command:
        """Check if a given string is a valid example of this command.

        If yes, then return an intialized version of this class with the command
        assigned.

        If no, return None.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_command() -> str:
        """Get the raw string command associated with this command."""
        pass

    @abstractmethod
    def execute(self):
        """Executes the next step of a given command, or update to a command."""
        pass


class MultiStepCommand(ABC, Command):
    @staticmethod
    @abstractmethod
    def create_from_partial_step(notification: Notification) -> MultiStepCommand:
        """Create a command from a notification that signals the start of a complete
        step.
        """
        pass


class CommandRegistry:
    def __init__(self):
        """Basic class to handle all"""
        self._commands = {}

    def register_command(self, command: Command | MultiStepCommand):
        """Registers a command as possible for users to execute."""
        if not isinstance(command, Command):
            raise ValueError(
                "command must be an instance of astrobot.commands._base.Command"
            )
        if command.command in self._commands:
            raise ValueError(
                f"Command {command} ({command.command}) already exists in registry."
            )
        self._commands[command.command] = command

    def deregister_command(self, command: Command | MultiStepCommand):
        """De-registers a command from the registry. After this point, it will not be
        possible for users to use without re-registering.

        Multi-step commands will be preserved; full reset would require additional work
        on the database.
        """
        pass

    def get_matching_command(self, notifcation: Notification):
        """Returns the command requested by notification."""
        if notifcation.reason != "mention":
            raise ValueError("notification reason must be a mention!")
        # todo finish this - will check all commands and hence return correct one, OR return an 'undefined' command

    def get_matching_multistep_command(self, notification: Notification):
        # todo
        pass
