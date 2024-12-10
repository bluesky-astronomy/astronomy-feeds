"""Signs a user up to the feed. Probably the most complicated command the bot can do!"""

from __future__ import annotations

from astrobot.database import (
    new_bot_action,
    update_bot_action,
    fetch_account_entry_for_did,
)
from importlib import resources
from astrobot import data

from ._base import MultiStepCommand
from ..post import send_post, send_thread
from atproto import Client, models, client_utils, IdResolver
from ..notifications import MentionNotification, LikeNotification, ReplyNotification
from ..moderation import MODERATORS, signup_user, cancel_signup
from typing import Callable


RULES_POSTS = [
    "Thank you for your interest in signing up to the Astronomy feeds! There are a few steps to this that I'll guide you through in this thread.\n\nThis bot is experimental; if you have any issues, please tag @emily.space, the bot's maintainer.",
    "Firstly, please note that you only need to sign up to the feed if you'd like to post to it. Anyone on Bluesky can read the feed!\n\nIn addition, you must be a professional, amateur, or student astronomer to post to the feeds. (It's also ok if you left academia but still want to sign up!)",
    "If the above is ok and you still want to sign up, then you'll need to agree to the feed rules below:\n\nIf you agree to follow them, then reply to this post with a 'yes'.",
]

rules_image_file = resources.files(data) / "rules.png"
with rules_image_file.open("rb") as f:
    rules_image = f.read()

RULES_IMAGES = {2: rules_image}

RULES_IMAGES_ALTS = {
    2: """Screenshot of the feed rules, which are:

1. To post to the feeds, you must be a professional/amateur/student in astronomy/astrophysics/astrobiology/planetary science/astronomy education—or you must represent an astronomy-related organization.
It’s also OK if you left academia but still want to sign up. You are still welcome here!

2. Be respectful of others in the community.
We will not tolerate discrimination of any kind; that means no racism, sexism, homophobia, transphobia, ableism, or any other kind of discrimination.

3. Content you post to the feeds must be appropriate, scientifically accurate, and not spam.
No off-topic posts, no misinformation/impersonation, and no spam, including repetitive or overly promotional material that clutters the feeds and detracts from meaningful interactions. AI usage should be minimized, and AI fakes or low-quality generative creations should be avoided. Ask a moderator if you aren’t sure about your content before you post.

4. Attribute content that is not your own.
You must credit the original author/creator of any content you post. Whenever possible, link to the original author/creator’s content.

5. Only limited promotion of items for sale is allowed—and they must be astronomy-related.
Independent creators may use the feeds occasionally to promote or sell their astronomy-related work. We ask you to limit your promotional posts to no more than once per day on the main Astronomy feed. Promotional posts should not be the majority of your contributions to the feeds.

If you ever have any concerns or issues with moderation, get in touch with @moderation.astronomy.blue."""
}


def _execute_rules_sent(command: SignupCommand, client: Client):
    print(f"SignupCommand: Sending feed rules to {command.notification.author.handle}")
    account_entries = fetch_account_entry_for_did(command.notification.author.did)
    already_signed_up = any(
        [account.is_valid for account in account_entries]
    )  # N.B. this is False if len(account_entries) == 0

    # Check if account already signed up
    if already_signed_up:
        root, parent = send_post(
            client,
            "You are already signed up to the feed and should be able to post to them! "
            "You can find instructions here:",
            quote=COMPLETE_QUOTES[1],
            root_post=command.notification.root_ref,
            parent_post=command.notification.parent_ref,
        )
        new_bot_action(command, latest_cid=parent.cid, latest_uri=parent.uri)
        return

    # Otherwise, start the process!
    root, parent = send_thread(
        client,
        RULES_POSTS,
        images=RULES_IMAGES,
        image_alts=RULES_IMAGES_ALTS,
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
    # Todo: could be more sophisticated here, e.g. if a smartass replies 'no' we probably don't want to have the bot act like an idiot and ask them to say yes
    valid_yes = {"yes", "y", "ye", "yeah", "yess", "yes.", "yes,", "yes!", "'yes'", "'yes", "yes'", "yea"}
    if not any([x in valid_yes for x in command.notification.words]):
        # Check if the bot has already replied
        from astrobot.config import HANDLE  # sorry it's here, avoids a circ import
        thread = client.get_post_thread(command.notification.notification.uri, parent_height=0)
        if any([HANDLE == reply.post.author.handle for reply in thread.thread.replies]):
            return
        
        # Otherwise, send some help text
        root, parent = send_post(
            client,
            "That doesn't look like a valid yes.\n\nIf you meant for it to be, you can try to reply to that post again with a 'yes' (without the apostrophes!).\n\nIf you don't accept the rules, then you won't be able to post to the feed.",
            root_post=command.notification.root_ref,
            parent_post=command.notification.parent_ref,
        )
        return

    root, parent = send_post(
        client,
        DESCRIPTION_TEXT,
        root_post=command.notification.root_ref,
        parent_post=command.notification.parent_ref,
    )
    update_bot_action(command, "get_description", parent.uri, parent.cid)


MODERATOR_TEXT = "Thanks! The last step now is to get a moderator to approve your signup. I'll let them know that you've applied!"


def _execute_get_moderator(command: SignupCommand, client: Client):
    print(
        f"SignupCommand: asking for moderator input on signup of {command.notification.author.handle}"
    )
    # Build the post to send from the current mod list
    text_builder = client_utils.TextBuilder()
    text_builder.text(MODERATOR_TEXT)
    # Tags currently removed - probably won't be added again...
    # for moderator in MODERATORS.get_accounts():
    #     text_builder.text(" ")
    #     text_builder.mention("(tag)", moderator)

    # Send it!
    root, parent = send_post(
        client,
        text_builder,
        root_post=command.notification.root_ref,
        parent_post=command.notification.parent_ref,
    )
    update_bot_action(command, "get_moderator", parent.uri, parent.cid)


COMPLETE_POSTS = [
    # 0 is made dynamically in the function
    # 1
    "Firstly, there are multiple feeds in the network that you can post to, covering many topics - from the general Astronomy feed to specific topics like Exoplanets. Here's a list of all of them:",
    # 2
    client_utils.TextBuilder()
    .text("Secondly, if you're new to Bluesky, then you may want to check out ")
    .link("this blog post", "https://emilydoesastro.com/posts/230824-bluesky-signup/")
    .text(" with tips on how to get started here, as well as our ")
    .link("starter pack", "https://bsky.app/starter-pack/emily.space/3kvvsi4qacz2p")
    .text(" with feeds and accounts to follow."),
    # 3
    client_utils.TextBuilder()
    .text(
        "Finally, if you ever have any problems, you can get in touch with the moderation account "
    )
    .mention("@moderation.astronomy.blue", "did:plc:ko747jc5ma4iarwwfwrlv2ct")
    .text(". Also, ")
    .mention("@emily.space", "did:plc:jcoy7v3a2t4rcfdh6i4kza25")
    .text(" is the admin of the feeds, and can help with technical issues."),
    # 4
    client_utils.TextBuilder().text(
        "Thanks so much for signing up! Let us know if you have any suggestions on how to improve the feeds or the community here.\n\nIMPORTANT: It can take up to 2 minutes for the server to refresh before you can post to the feed."
    ),
]

COMPLETE_QUOTES = {
    # @emily.space thread of all feeds, with details:
    1: models.ComAtprotoRepoStrongRef.Main(
        uri="at://did:plc:xy2zorw2ys47poflotxthlzg/app.bsky.feed.post/3lau3lw3mk22b",
        cid="bafyreihe2ooso6qrhxs43wvd3bqiq4hai2qkcz6n2yerfd5qgoiqcjavn4",
    )
}


def _execute_complete(
    command: SignupCommand, client: Client, reply_in_thread: bool = True
):
    print(f"SignupCommand: signing up {command.notification.author.handle}")

    # Since we take a LikeNotification which doesn't define root_ref, if we want to
    # continue replying in the thread then we'll have to get root_ref
    parent_ref, root_ref = None, None
    if reply_in_thread:
        command.notification.fetch_root_ref(client)
        parent_ref, root_ref = (
            command.notification.parent_ref,
            command.notification.root_ref,
        )

    # Get the original account's handle for nice formatting reasons + db reasons
    handle = (
        IdResolver(timeout=30).did.resolve(command.notification.action.did).get_handle()
    )

    # Dynamically make a first post that includes their name
    first_post = [
        client_utils.TextBuilder()
        .mention("@" + handle, command.notification.action.did)
        .text(
            ", congratulations! 🎉 You're now signed up to the Astronomy feeds, and can post to them.\n\nHere's all the information you need to know:"
        ),
    ]

    # Then, send that first post + some other info ones
    root, parent = send_thread(
        client,
        first_post + COMPLETE_POSTS,
        quotes=COMPLETE_QUOTES,
        root_post=root_ref,
        parent_post=parent_ref,
    )

    # Sign them up
    signup_user(
        command.notification.action.did,
        command.notification.author.did,
        handle=handle,
        valid=True,
    )

    # Finish this multi-step bot action.
    update_bot_action(command, "complete", parent.uri, parent.cid)


def _execute_cancel(command: SignupCommand, client: Client, reply_in_thread: bool = True):
    print(f"SignupCommand: cancelling signup {command.notification.author.handle}")
    root, parent = send_thread(
        client,
        ["Signup request cancelled."],
        #quotes=COMPLETE_QUOTES,
        root_post=command.notification.root_ref,
        parent_post=command.notification.parent_ref,
    )

    update_bot_action(command, "complete", parent.uri, parent.cid)
    cancel_signup(command.notification.action.did, command.notification.author.did)


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

        # Check to see if moderator liked or replied to the bot's previous post
        if stage == "get_moderator" and is_moderator:
            if is_like:
                return SignupCommand(notification, _execute_complete)
            if notification.words[0] == "cancel":
                return SignupCommand(notification, _execute_cancel)

        print(
            f"Attempted to match a notification to command {MultiStepCommand.command}, "
            f"but notification is not a valid match. Type: {notification.__class__}; "
            f"author: {notification.author.handle}"
        )
        return None

    def execute_good_permissions(self, client: Client):
        """Execute the command. Defined in __init__."""
        return self.execute_command(self, client)
