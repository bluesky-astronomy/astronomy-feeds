"""Signs a user up to the feed."""

from __future__ import annotations

from astrobot.database import new_bot_action, update_bot_action
from ._base import MultiStepCommand
from ..post import send_post, send_thread
from atproto import Client, models, client_utils
from ..notifications import MentionNotification, LikeNotification, ReplyNotification
from ..moderation import MODERATORS, signup_user
from typing import Callable


RULES_POSTS = [
    "Thank you for your interest in signing up to the Astronomy feeds! There are a few steps to this that I'll guide you through.\n\nThis bot is experimental; if you have any issues, please tag (at)emily.space, the bot's maintainer.\n\nFirstly, you'll need to agree to the rules of the feeds:",
    "1. You must be a professional, amateur, aspiring, or in-training astronomer to join.\n\nIt's also absolutely ok if you left academia but still want to sign up - you are still an astronomer and you are welcome here!",
    "2. Be respectful of others in the community.\n\nWe won't tolerate discrimination of any kind; that means no racism, sexism, homophobia, transphobia, ableism, or any other kind of discrimination.",
    "3. Content that you post to the feeds must be appropriate for them.\n\nThat means:\n- No misinformation/impersonation\n- No spamming\n-No off-topic posts.",
    "4. Attribute content that is not your own!\n\nIf content is not your own, then you must credit the original author. Where possible, you should link to the original author's content.",
    "If you agree to all of the above, then reply to this post with a 'yes'.",
]


def _execute_rules_sent(command: SignupCommand, client: Client):
    print(f"SignupCommand: Sending feed rules to {command.notification.author.handle}")
    root, parent = send_thread(
        client,
        RULES_POSTS,
        root_post=command.notification.root_ref,
        parent_post=command.notification.parent_ref,
    )
    new_bot_action(
        command, stage="rules_sent", latest_cid=parent.cid, latest_uri=parent.uri
    )


DESCRIPTION_TEXT = "Great! 😊\n\nNext off, please reply to this post with one or two sentences about why you'd like to join the feeds.\n\nFor instance: are you an astrophotographer? Are you currently studying/working in astronomy? Or whatever else!"


def _execute_get_description(command: SignupCommand, client: Client):
    print(
        f"SignupCommand: asking for signup description from {command.notification.author.handle}"
    )

    # Check to see if they replied with yes
    # Todo: could be more sophisticated here, e.g. if a smartass replies 'no'
    valid_yes = {"yes", "y", "ye", "yeah", "yess", "yes.", "yes,"}
    if command.notification.words not in valid_yes:
        return

    root, parent = send_post(
        client,
        DESCRIPTION_TEXT,
        root_post=command.notification.root_ref,
        parent_post=command.notification.parent_ref,
    )
    update_bot_action(command, "get_description", parent.uri, parent.cid)


MODERATOR_TEXT = "Thanks! The last step now is to get input from a moderator. I'll mention them here to get their attention: "


def _execute_get_moderator(command: SignupCommand, client: Client):
    print(
        f"SignupCommand: asking for moderator input on signup of {command.notification.author.handle}"
    )
    # Build the post to send from the current mod list
    text_builder = client_utils.TextBuilder()
    text_builder.text(MODERATOR_TEXT)
    # Todo: this could overflow the post length limit if we get too many mods!
    for moderator in MODERATORS.get_accounts():
        text_builder.mention("account", moderator)

    # Send it!
    root, parent = send_post(
        client,
        text_builder,
        root_post=command.notification.root_ref,
        parent_post=command.notification.parent_ref,
    )
    update_bot_action(command, "get_moderator", parent.uri, parent.cid)


# COMPLETE_POSTS = [
#     "Congratulations! 🎉 You're now signed up to the Astronomy feeds, and can post to them.\n\nHere's all the information you need to know:",
#     "Firstly, there are multiple feeds in the network, covering many topics - from the general Astronomy feed to specific topics like Exoplanets. Here's a list of all of them:",
#     client_utils.TextBuilder()
# ]

# COMPLETE_QUOTES = {
#     1: models.ComAtprotoRepoStrongRef.Main()
# }


def _execute_complete():
    pass

# def _execute_complete(command: SignupCommand, client: Client):
#     print(f"SignupCommand: signing up {command.notification.author.handle}")
#     # Since the notification type is a like and that doesn't define root ref, we need to
#     # manually make one first
#     root_ref = models.ComAtprotoRepoStrongRef.Main(
#         cid=command.notification.action.parent_cid,
#         uri=command.notification.action.parent_uri,
#     )

#     # Then, send all info to the user
#     root, parent = send_post(
#         client,
#         text_builder,
#         root_post=root_ref,
#         parent_post=command.notification.parent_ref,
#     )

#     # Sign them up (we grab their handle again first)
#     response = client.com.atproto.repo.describe_repo(
#         params={"repo": command.notification.action.did}
#     )
#     handle = response["handle"]

#     signup_user(
#         command.notification.action.did,
#         handle,
#         command.notification.author.did,
#         valid=True,
#     )

#     # Finish this multi-step bot action.
#     update_bot_action(command, "complete", parent.uri, parent.cid)


class SignupCommand(MultiStepCommand):
    """Sign up a user to the feeds.

    This command is multi-step, and has the following steps:
    'rules_sent':
    USER: mention with "@bot.astronomy.blue signup"
    BOT: send rules

    'get_description':
    USER: reply "yes"
    BOT: ask user to reply with why they want to join the feed

    'get_moderator':
    USER: reply with answer
    BOT: reply thanks and tag moderators

    'complete':
    MODERATOR: like bot last post
    BOT: tell user they are signed up, perform db actions, send further instructions
    """

    command = "signup"

    def __init__(
        self,
        notification: MentionNotification,
        execute_method: Callable[[SignupCommand, Client], None] = _execute_rules_sent,
    ):
        self.notification = notification
        self.execute_command = execute_method

    @staticmethod
    def is_instance_of(notification: MentionNotification) -> None | SignupCommand:
        if notification.words[0] == SignupCommand.command:
            return SignupCommand(notification)

        # Additional spellings
        if notification.words[0] == "sign" and notification.words[1] == "up":
            return SignupCommand(notification)
        if notification.words[0] == "sign-up":
            return SignupCommand(notification)

    @staticmethod
    def create_from_partial_step(
        notification: LikeNotification | ReplyNotification,
    ) -> MultiStepCommand | None:
        """Create a command from a notification that signals the start of a complete
        step. Returns None if the notification isn't a valid start of this command
        (e.g. if the author doesn't have the correct permissions.)
        """
        stage = notification.action.stage
        is_like = isinstance(notification, LikeNotification)
        is_reply = isinstance(notification, ReplyNotification)
        is_author = notification.author.did == notification.action.did
        is_moderator = notification.author.did in MODERATORS.get_accounts()

        # Check to see if user has accepted the rules
        if stage == "rules_sent" and is_author and is_reply:
            return SignupCommand(notification, _execute_get_description)

        # Check to see if user replied with a post
        if stage == "get_description" and is_author and is_reply:
            return SignupCommand(notification, _execute_get_moderator)

        # Check to see if moderator liked the bot's previous post
        if stage == "get_moderator" and is_moderator and is_like:
            return SignupCommand(notification, _execute_complete)

        print(
            f"Attempted to match a notification to command {MultiStepCommand.command}, "
            f"but notification is not a valid match. Type: {notification.__class__}; "
            f"author: {notification.author.handle}"
        )
        return None

    def execute(self, client: Client):
        """Execute the command. Defined in __init__."""
        return self.execute_command(self, client)
