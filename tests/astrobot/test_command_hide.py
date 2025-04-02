from datetime import datetime

from astrofeed_lib.database import BotActions, ModActions, Post, Account
from astrofeed_lib.database import DBConnection
from astrofeed_lib.config import ASTROFEED_PRODUCTION

from astrobot.commands.moderation.hide import ModeratorHideCommand
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref
from astrobot.config import HANDLE
from astrobot.post import get_embed_info, get_reply_info

def test_hide(test_db_conn, mock_client):
        # just to be safe, make sure there's no risk of connecting to the live database
    if ASTROFEED_PRODUCTION:
        raise ConnectionRefusedError("Attempting to run offline unit test in production mode; aborting.")

    # create a hide command objects with a mock notification
    # should we also test the command failing (with an inappropriate mod level, already hidden post, etc...many ways)
    with DBConnection():
        unhidden_post = Post.select().where(~Post.hidden)[-1]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level

    hide_reply_ref = build_reply_ref(         # we don't store root uri and cid in our Post table, leaving those as default values
        parent_ref_cid = unhidden_post.cid, 
        parent_ref_uri = unhidden_post.uri,
    )
    hide_notification = build_notification(
        "mention reply", 
        record_text=f"@{HANDLE} hide", 
        record_reply=hide_reply_ref, 
        author_did=moderator_account.did
    )
    hide_command = ModeratorHideCommand(MentionNotification(hide_notification))

    # act
    hide_command.execute(mock_client)

    # extract quantities of interest and make assertions
    call_signature = mock_client.send_post_call_signature
    parent_ref = hide_command.notification.parent_ref
    root_ref = hide_command.notification.root_ref
    assert call_signature["text"] == "Post hidden from feeds successfully."
    assert call_signature["profile_identify"]is None
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)
    assert call_signature["embed"] == get_embed_info(None, None) # hide command calls astrobot.post.send_post embed=quote=None
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None

    with DBConnection():
        botactions_entry = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        modactions_entry = ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & (ModActions.did_user == unhidden_post.author))\
            .order_by(ModActions.indexed_at.desc())[0]
    assert botactions_entry.indexed_at < datetime.utcnow()
    assert botactions_entry.did == hide_command.notification.author.did
    assert botactions_entry.type == hide_command.command
    assert botactions_entry.stage == "complete"
    assert botactions_entry.parent_uri == parent_ref.uri
    assert botactions_entry.parent_cid == parent_ref.cid
    assert botactions_entry.latest_uri == parent_ref.uri
    assert botactions_entry.latest_cid == parent_ref.cid
    assert botactions_entry.complete
    assert botactions_entry.authorized
    assert botactions_entry.checked_at < datetime.utcnow()

    assert modactions_entry.indexed_at < datetime.utcnow()
    assert modactions_entry.did_mod == hide_notification.author.did
    assert modactions_entry.did_user == hide_notification.record.reply.parent.uri.replace("at://", "").split("/")[0]
    assert modactions_entry.expiry is None