"""Base class for commands."""

from __future__ import annotations
from abc import ABC, abstractmethod
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from astrofeed_lib.database import BotActions

from astrobot.commands.unrecognized import UnrecognizedCommand


class Command(ABC):
    command = ""  # should be set by subclasses
    level = "user"  # user or moderator; user by default

    @staticmethod
    @abstractmethod
    def is_instance_of(words: list[str], notification: Notification) -> None | Command:
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


class MultiStepCommand(Command):
    @staticmethod
    @abstractmethod
    def create_from_partial_step(
        notification: Notification, command_stage: str, database_entry: BotActions
    ) -> MultiStepCommand:
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
        if not isinstance(command, Command):
            raise ValueError(
                "command must be an instance of astrobot.commands._base.Command"
            )
        if command.command not in self._commands:
            raise ValueError(
                f"Command {command} ({command.command}) already exists in registry."
            )
        self._commands.pop([command.command])

    def get_matching_command(self, notification: Notification, handle: str):
        """Returns the command requested by notification."""
        if notification.reason != "mention":
            raise ValueError("notification reason must be a mention!")

        # Get all words after 'handle' in the post's text
        words = extract_command_arguments(notification, handle)
        if isinstance(words, UnrecognizedCommand):
            return words

        # Find a matching command
        for command in self._commands:
            result = self._commands[command].is_instance_of(words, notification)
            if result is not None:
                return result

        # Otherwise, say it isn't recognized.
        return UnrecognizedCommand(
            notification, extra=" Reason: command not recognized."
        )

    def get_matching_multistep_command(
        self, notification: Notification, command_type: str, command_stage: str
    ):
        if command_type not in self._commands:
            raise ValueError(f"Command of type {command_type} is not in the registry!")
        command = self._commands[command_type]

        if not isinstance(command, MultiStepCommand):
            raise ValueError(f"Command of type {command_type} is not multi-step!")

        return command.create_from_partial_step(notification, command_stage)


def extract_command_arguments(notification: Notification, handle: str):
    """Extracts the command and any arguments from the text."""
    words = Notification.record.text.split(" ")
    if handle not in words:
        return UnrecognizedCommand(notification, extra=" Reason: missing mention.")

    mention_index = words.index(handle)

    if mention_index >= len(words) - 1:
        return UnrecognizedCommand(
            notification, extra=" Reason: cannot find command after mention."
        )

    return words[mention_index + 1 :]
