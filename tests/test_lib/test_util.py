from datetime import datetime, timezone

from astrobot.commands._base import Command
from astrobot.post import get_embed_info, get_reply_info

from astrofeed_lib.database import BotActions, ModActions, Account
from astrofeed_lib.database import DBConnection

from tests.conftest import MockClient


def check_call_signature(
    command: Command,
    mock_client: MockClient,
    # currently, the expected post text is all that varies that isn't contained in the command itself
    text: str | list[str],
):
    """Checks that the the call signature recorded by a MockClient.send_post call reflects data in an executed command.

    Most of the details of what we expect to be in this call come from the command object and its
    associated notification; the expected post text is the only thing that doesn't, so it gets its
    own argument.

    note: commands typically perform the following call to astrobot.post.send_post()
    >> send_post(
    >>     client=client,
    >>     text=explanation,
    >>     root_post=self.notification.root_ref,
    >>     parent_post=self.notification.parent_ref,
    >> )
    (additional argument name specifiers added to the first two arguments for clarity),
    which leaves its other arguments as defaults image=None, image_alt=None, embed=None, quote=None

    Within astrobot.post.send_post, we then have
    >> reply_info = get_reply_info(root_post, parent_post)
    >> embed_info = get_embed_info(embed, quote)
    before finally having the call
    >> client.send_post(text=text, reply_to=reply_info, embed=embed_info)
    which leaves its other arguments as defaults profile_identify = None, langs = None, facets = None

    The result of all of this is that only the text and reply_to arguments can possibly have any
    information that is not specified in the defaults of the astrobot.post.send_post and
    atproto.Client.send_post funtions; all other information should be the same for each case,
    and will be determined purely by non-overidden default values from the function definitions.
    """
    call_signature = mock_client.send_post_call_signature
    parent_ref = command.notification.parent_ref
    root_ref = command.notification.root_ref

    # information specific to each case
    if (
        type(text) is str
    ):  # hack to allow for testing multiple possibilities at once (mostly for joke command)
        text = [text]
    assert call_signature["text"] in text
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)

    # information defined by non-overidden funtion definition default values
    assert call_signature["profile_identify"] is None
    assert call_signature["embed"] == get_embed_info(None, None)
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None


def check_botactions_entry(command: Command, botaction: BotActions):
    """Checks that the BotActions table entry reflects data in an executed command."""
    with DBConnection():
        mod_level = (
            Account.select()
            .where(Account.did == command.notification.author.did)[0]
            .mod_level
        )

    assert botaction.indexed_at < datetime.now(timezone.utc).replace(tzinfo=None)
    assert botaction.did == command.notification.author.did
    assert botaction.type == command.command
    assert botaction.stage == "complete"
    assert botaction.parent_uri == command.notification.parent_ref.uri
    assert botaction.parent_cid == command.notification.parent_ref.cid
    assert botaction.latest_uri == command.notification.parent_ref.uri
    assert botaction.latest_cid == command.notification.parent_ref.cid
    assert botaction.complete
    assert botaction.authorized == (mod_level >= command.level)
    assert botaction.checked_at < datetime.now(timezone.utc).replace(tzinfo=None)


def check_modactions_entry(command: Command, did_user: str, modaction: ModActions):
    """Checks that the ModActions table entry reflects data in an executed command."""
    assert modaction.indexed_at < datetime.now(timezone.utc).replace(tzinfo=None)
    assert modaction.did_mod == command.notification.notification.author.did
    assert modaction.did_user == did_user
    assert modaction.expiry is None
