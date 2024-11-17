"""Base class for commands."""

from __future__ import annotations
from abc import ABC, abstractmethod
from atproto import Client
from ..notifications import LikeNotification, ReplyNotification, MentionNotification
from ..post import send_post
from astrobot.moderation import MODERATORS
from astrobot.database import new_bot_action


class Command(ABC):
    command = ""  # should be set by subclasses
    level = 0  # user or moderator level; user (0) by default. If -1, only users can use this command.

    @staticmethod
    @abstractmethod
    def is_instance_of(notification: MentionNotification) -> None | Command:
        """Check if a given string is a valid example of this command.

        If yes, then return an intialized version of this class with the command
        assigned.

        If no, return None.
        """
        pass

    def execute(self, client: Client):
        """Executes the next step of a given command, or update to a command."""
        if reason := self.user_cannot_use_command():
            self.execute_no_permissions(client, reason)
        self.execute_good_permissions(client)

    def user_cannot_use_command(self):
        """Work out if a user is allowed to use this command based on the command's
        self.level. Returns False if they *can* use it, or True if they cannot.
        
        Command levels explained:
        =0: any user may use
        >0: any moderator with a level greater than or equal to level may use
        <0: any moderator with a level greater than or equal to may *not* use
        """
        # Level == 0 -> no permissions are on this command!
        if self.level == 0:
            return False

        # Level < 0 -> requires NOT having mod permissions
        author_did = self.notification.author.did

        if self.level < 0:
            if author_did in MODERATORS.get_accounts_above_level(self.level * -1):
                return True
            return False

        # Hence, must have level > 0 -> requires mod permissions
        if author_did in MODERATORS.get_accounts_above_level(self.level):
            return False

        # Todo: block banned/muted users from ever touching a command on the bot
        # Todo: make it so a banned user, if trying to use a command, actually gets banned on a Bluesky level so that they physically can't interact with it
        return f"Lacking required moderator level ({self.level})"

    def execute_no_permissions(self, client: Client, reason: str):
        """Tells the user that they did not have the required permissions to run this
        command.
        """
        send_post(
            client,
            "Sorry, but you don't have the required permissions to run this command. "
            f"Reason: {reason}",
            root_post=self.notification.root_ref,
            parent_post=self.notification.parent_ref,
        )

        # Record this attempt to use a mod command
        new_bot_action(self, authorized=False)

    @abstractmethod
    def execute_good_permissions(self, client: Client):
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
