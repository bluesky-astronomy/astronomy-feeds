from datetime import datetime

from astrofeed_lib.database import BotActions, ModActions, Post, Account
from astrofeed_lib.database import DBConnection

from astrobot.commands.moderation.hide import ModeratorHideCommand
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref
from astrobot.config import HANDLE
from astrobot.post import get_embed_info, get_reply_info

def test_success(test_db_conn, mock_client):
    # gather necessary database entries/info
    with DBConnection():
        target_post_before = Post.select().where(~Post.hidden)[-1]
        author_account_before = Account.select().where(Account.did == target_post_before.author)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level

    # create a hide command objects with a mock notification
    hide_reply_ref = build_reply_ref(         # we don't store root uri and cid in our Post table, leaving those as default values
        parent_ref_cid = target_post_before.cid,
        parent_ref_uri = target_post_before.uri,
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

    # assert that call to "atproto.Client.send_post" has correct information
    call_signature = mock_client.send_post_call_signature
    parent_ref = hide_command.notification.parent_ref
    root_ref = hide_command.notification.root_ref
    assert call_signature["text"] == "Post hidden from feeds successfully."
    assert call_signature["profile_identify"]is None
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)
    assert call_signature["embed"] == get_embed_info(None, None) # hide command calls astrobot.post.send_post embed=quote=None
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None

    # refresh old database entries and get new ones
    with DBConnection():
        target_post_after    = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_account_after = Account.select().where(Account.did == author_account_before.did)[0]
        botaction = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        modaction = ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & (ModActions.did_user == author_account_before.did))\
            .order_by(ModActions.indexed_at.desc())[0]
    assert target_post_after.hidden
    assert author_account_after.hidden_count == author_account_before.hidden_count + 1
    assert botaction.indexed_at < datetime.utcnow()
    assert botaction.did == hide_command.notification.author.did
    assert botaction.type == hide_command.command
    assert botaction.stage == "complete"
    assert botaction.parent_uri == parent_ref.uri
    assert botaction.parent_cid == parent_ref.cid
    assert botaction.latest_uri == parent_ref.uri
    assert botaction.latest_cid == parent_ref.cid
    assert botaction.complete
    assert botaction.authorized
    assert botaction.checked_at < datetime.utcnow()

    assert modaction.indexed_at < datetime.utcnow()
    assert modaction.did_mod == hide_notification.author.did
    assert modaction.did_user == hide_notification.record.reply.parent.uri.replace("at://", "").split("/")[0]
    assert modaction.expiry is None

def test_failure_insufficient_mod_level(test_db_conn, mock_client):
    # create a hide command objects with a mock notification
    with DBConnection():
        target_post_before = Post.select().where(Post.hidden)[-1]
        author_account_before = Account.select().where(Account.did == target_post_before.author)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(ModActions.indexed_at.desc())[0]

    hide_reply_ref = build_reply_ref(         # we don't store root uri and cid in our Post table, leaving those as default values
        parent_ref_cid = target_post_before.cid, 
        parent_ref_uri = target_post_before.uri
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
    assert call_signature["text"] == "Unable to hide post: post already hidden."
    assert call_signature["profile_identify"]is None
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)
    assert call_signature["embed"] == get_embed_info(None, None) # hide command calls astrobot.post.send_post embed=quote=None
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None

    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_account_after = Account.select().where(Account.did == author_account_before.did)[0]
        botaction = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        n_modactions = \
            ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & 
                   (ModActions.did_user == author_account_before.did) & 
                   (ModActions.indexed_at > latest_modaction_before.indexed_at))\
            .count()

    # make sure nothing happened (no modaction should have been added)
    assert author_account_after.hidden_count == author_account_before.hidden_count
    assert target_post_after.hidden and target_post_before.hidden
    assert n_modactions == 0

    # botaction is normal
    assert botaction.indexed_at < datetime.utcnow()
    assert botaction.did == hide_command.notification.author.did
    assert botaction.type == hide_command.command
    assert botaction.stage == "complete"
    assert botaction.parent_uri == parent_ref.uri
    assert botaction.parent_cid == parent_ref.cid
    assert botaction.latest_uri == parent_ref.uri
    assert botaction.latest_cid == parent_ref.cid
    assert botaction.complete
    assert botaction.authorized
    assert botaction.checked_at < datetime.utcnow()

def test_failure_post_already_hidden(test_db_conn, mock_client):
    # create a hide command objects with a mock notification
    with DBConnection():
        target_post_before = Post.select().where(Post.hidden)[-1]
        author_account_before = Account.select().where(Account.did == target_post_before.author)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(ModActions.indexed_at.desc())[0]

    hide_reply_ref = build_reply_ref(         # we don't store root uri and cid in our Post table, leaving those as default values
        parent_ref_cid = target_post_before.cid, 
        parent_ref_uri = target_post_before.uri
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
    assert call_signature["text"] == "Unable to hide post: post already hidden."
    assert call_signature["profile_identify"]is None
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)
    assert call_signature["embed"] == get_embed_info(None, None) # hide command calls astrobot.post.send_post embed=quote=None
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None

    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_account_after = Account.select().where(Account.did == author_account_before.did)[0]
        botaction = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        n_modactions = \
            ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & 
                   (ModActions.did_user == author_account_before.did) & 
                   (ModActions.indexed_at > latest_modaction_before.indexed_at))\
            .count()

    # make sure nothing happened (no modaction should have been added)
    assert author_account_after.hidden_count == author_account_before.hidden_count
    assert target_post_after.hidden and target_post_before.hidden
    assert n_modactions == 0

    # botaction is normal
    assert botaction.indexed_at < datetime.utcnow()
    assert botaction.did == hide_command.notification.author.did
    assert botaction.type == hide_command.command
    assert botaction.stage == "complete"
    assert botaction.parent_uri == parent_ref.uri
    assert botaction.parent_cid == parent_ref.cid
    assert botaction.latest_uri == parent_ref.uri
    assert botaction.latest_cid == parent_ref.cid
    assert botaction.complete
    assert botaction.authorized
    assert botaction.checked_at < datetime.utcnow()