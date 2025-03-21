"""A registry of all commands."""

import warnings
from astrobot.commands.unrecognized import UnrecognizedCommand
from ._base import Command, MultiStepCommand
from ..notifications import LikeNotification, ReplyNotification, MentionNotification


class CommandRegistry:
    def __init__(self):
        """Basic class to handle all"""
        self._commands = {}

    def register_command(self, command):
        """Registers a command as possible for users to execute."""
        if not issubclass(command, Command):
            raise ValueError(
                "command must be an instance of astrobot.commands._base.Command"
            )
        if command.command in self._commands:
            raise ValueError(
                f"Command {command} ({command.command}) already exists in registry."
            )
        self._commands[command.command] = command

    def register_commands(self, commands: list):
        """Registers a list of commands as possible for users to execute."""
        for command in commands:
            self.register_command(command)

    def deregister_command(self, command):
        """De-registers a command from the registry. After this point, it will not be
        possible for users to use without re-registering.

        Multi-step commands will be preserved; full reset would require additional work
        on the database.
        """
        if not issubclass(command, Command):
            raise ValueError(
                "command must be an instance of astrobot.commands._base.Command"
            )
        if command.command not in self._commands:
            raise ValueError(
                f"Command {command} ({command.command}) already exists in registry."
            )
        self._commands.pop([command.command])

    def get_matching_command(self, notification: MentionNotification):
        """Returns the command requested by notification."""
        if len(notification.words) == 0:
            return UnrecognizedCommand(
                notification, extra=" Reason: no command specified."
            )

        # Find a matching command
        for command in self._commands:
            result = self._commands[command].is_instance_of(notification)
            if result is not None:
                return result

        # Otherwise, say it isn't recognized.
        commands_as_list = ", ".join([f"'{x}'" for x in self._commands.keys()])
        return UnrecognizedCommand(
            notification, extra=f"\n\nValid commands: {commands_as_list}"
        )  # Todo could overflow post limit when more added; also will contain mod commands

    def get_matching_multistep_command(
        self, notification: LikeNotification | ReplyNotification
    ):
        if notification.action.type not in self._commands:
            warnings.warn(
                f"Command of type {notification.action.type} is not in the registry! "
                "It may have been disabled.",
                RuntimeWarning,
            )
        command = self._commands[notification.action.type]

        if not issubclass(command, MultiStepCommand):
            # If this ever happens, then it means the database had an error!
            raise ValueError(
                f"Command of type {notification.action.type} is not multi-step!"
            )

        return command.create_from_partial_step(notification)

    def list_commands(self) -> list[str]:
        return list(self._commands.keys())

    def list_multistep_commands(self) -> list[str]:
        command_names = []
        for command_name, command in self._commands.items():
            if issubclass(command, MultiStepCommand):
                command_names.append(command_name)
        return command_names
