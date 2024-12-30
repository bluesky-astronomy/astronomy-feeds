"""Hide a post from the feeds."""

from __future__ import annotations

from atproto import Client
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification
from astrobot.database import new_bot_action
from astrobot.moderation import hide_post
from astrobot.post import send_post


class ModeratorHideCommand(Command):
    command = "hide"
    level = 2

    def __init__(self, notification: MentionNotification):
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorHideCommand:
        if notification.words[0] == ModeratorHideCommand.command:
            return ModeratorHideCommand(notification)

    def execute_good_permissions(self, client: Client):
        # Default failure case
        explanation = "Unable to hide post: this command must be in reply to the post to hide."
        
        # Check that this post is a reply to something
        if hasattr(self.notification.notification.record, "reply"):
            # Attempt to hide the post it's replied to
            uri_to_hide = self.notification.notification.record.reply.parent.uri
            author_did = uri_to_hide.replace("at://", "").split("/")[0]
            mod_did = self.notification.author.did
            explanation = hide_post(uri_to_hide, author_did, mod_did)

        # & inform the user
        send_post(
            client,
            explanation,
            root_post=self.notification.root_ref,
            parent_post=self.notification.parent_ref,
        )
        new_bot_action(self)
