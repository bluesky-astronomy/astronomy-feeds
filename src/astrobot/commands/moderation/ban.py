"""Ban a user from the feeds."""

from __future__ import annotations

from atproto import Client, IdResolver
from astrobot.commands._base import Command
from astrobot.notifications import MentionNotification
from astrobot.database import new_bot_action
from astrobot.moderation import ban_user
from astrobot.post import send_post


class ModeratorBanCommand(Command):
    command = "ban"
    level = 3

    def __init__(self, notification: MentionNotification):
        self.notification = notification

    @staticmethod
    def is_instance_of(
        notification: MentionNotification,
    ) -> None | ModeratorBanCommand:
        if notification.words[0] == ModeratorBanCommand.command:
            return ModeratorBanCommand(notification)

    def execute_good_permissions(self, client: Client):
                # Default failure case
        explanation = (
            "Unable to execute ban; this command must specify the handle of the user to ban."
        )

        # if command post is a reply, ban replied-to user
        if len(self.notification.words) > 1:
            handle_to_ban = self.notification.words[1]
            # note: to check handle validity, we should check whether the handle actually resolves and use the DID from there, rather 
            # than checking whether we have an entry with that handle already; in case whoever we are trying to ban has changed their 
            # handle since they registered to post
            if did_to_ban := IdResolver(timeout=30).handle.resolve(handle_to_ban):
                mod_did = self.notification.author.did
                ban_reason = " ".join(self.notification.words[2:]) # perhaps this should be different? multi-step command to get reason?
                explanation = ban_user(did=did_to_ban, did_mod=mod_did, reason=ban_reason)
            else:
                explanation = (
                    f"Unable to execute ban; not able to resolve given user handle \"{handle_to_ban}\""
                )

        # & inform the user
        send_post(
            client,
            explanation,
            root_post=self.notification.root_ref,
            parent_post=self.notification.parent_ref,
        )
        new_bot_action(self)
