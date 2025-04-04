from datetime import datetime
from dataclasses import asdict

from astrofeed_lib.database import BotActions, ModActions, Post, Account
from astrofeed_lib.database import DBConnection

from astrobot.commands.moderation.hide import ModeratorHideCommand
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref
from astrobot.config import HANDLE
from astrobot.post import get_embed_info, get_reply_info
from test_lib.test_database import testdb_account_entry, generate_testdb_post_by_author

def test_success(test_db_conn, mock_client):
    '''Tests standard expected success case.
    
    For this case, a BotAction and ModAction entry should be created; the Post entry for the targeted 
    post should be modified to hide it, and the Account entry for its author modified to increment the 
    hidden_count by one; and a post should be sent in reply to the instigating post (by a mod, in reply 
    to the post to hide) to indicate the success of the action.
    '''
    # connect & collect
    with DBConnection():
        target_post_before = Post.select().where(~Post.hidden)[-1]
        author_account_before = Account.select().where(Account.did == target_post_before.author)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level

    # make our hide command
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

    # connect & collect
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

def test_success_multiple_author_entries(test_db_conn, mock_client):
    '''Tests success case in which target post's author has multiple entries in Account table
    
    For this case, a BotAction and ModAction entry should be created as usual; the Post entry for the 
    targeted post should be modified to hide it, and *only the first* Account entry for its author (
    sorted however the table istelf is ordered) is modified to increment the hidden_count by one; 
    and a post should be sent in reply to the instigating post to indicate the success of the action.
    '''
    # connect & collect; and duplicate the post's author's Account entry if there aren't already duplicates
    with DBConnection() as conn:
        target_post_before = Post.select().where(~Post.hidden)[-1]
        author_account_select = Account.select().where(Account.did == target_post_before.author)
        if author_account_select.count() > 1:
            # database already has duplicate entries, (gotta) collect them all
            author_duplicates_before = list(author_account_select)
        else:
            # insert a duplicate and collect them
            author_account_dict = author_account_select.dicts()[0]
            author_account_dict["id"] = Account.select().order_by(Account.id.desc())[0].id + 1
            with conn.atomic():
                Account.insert(author_account_dict).execute()
            author_duplicates_before = list(Account.select().where(Account.did == target_post_before.author))
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level

    # make our hide command
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

    # post-act connect & collect and assertions
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
        target_post_after    = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_duplicates_after = list(Account.select().where(Account.did == author_duplicates_before[0].did))
        botaction = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        modaction = ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & (ModActions.did_user == author_duplicates_before[0].did))\
            .order_by(ModActions.indexed_at.desc())[0]

    # first author entry should have been modified; others should be untouched
    assert author_duplicates_after[0].hidden_count == author_duplicates_before[0].hidden_count + 1
    for author_after,author_before in zip(author_duplicates_after[1:], author_duplicates_before[1:]):
        assert author_after.hidden_count == author_before.hidden_count

    # everything else checked as normal
    assert target_post_after.hidden
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

def test_success_multiple_post_entries(test_db_conn, mock_client):
    '''Tests success case in which target post has multiple entries in Post table
    
    For this case, a BotAction and ModAction entry should be created as usual; *only the first* Post 
    entry for the targeted post (sorted however the table istelf is ordered) should be modified to 
    hide it, and the Account entry for its author should be modified to increment the hidden_count 
    by one; and a post should be sent in reply to the instigating post to indicate the success of the 
    action.
    '''
    # connect & collect; and duplicate the post entry if there aren't already duplicates
    with DBConnection() as conn:
        target_post_initial = Post.select().where(~Post.hidden)[-1]

        # search for duplicates is done by URI, so we'll duplicated based on that
        target_post_select = Post.select().where(Post.uri == target_post_initial.uri)
        if target_post_select.count() > 1:
            # database already has duplicate entries, (gotta) collect them all
            target_post_duplicates_before = list(target_post_select)
        else:
            # insert a duplicate and collect them
            target_post_dict = target_post_select.dicts()[0]
            target_post_dict["id"] = Post.select().order_by(Post.id.desc())[0].id + 1
            with conn.atomic():
                Post.insert(target_post_dict).execute()
            target_post_duplicates_before = list(Post.select().where(Post.uri == target_post_initial.uri))

        author_account_before = Account.select().where(Account.did == target_post_duplicates_before[0].author)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level

    # make our hide command
    hide_reply_ref = build_reply_ref(         # we don't store root uri and cid in our Post table, leaving those as default values
        parent_ref_cid = target_post_duplicates_before[0].cid,
        parent_ref_uri = target_post_duplicates_before[0].uri
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

    # post-act connect & collect and assertions
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
        target_post_duplicates_after    = list(Post.select().where(Post.uri == target_post_duplicates_before[0].uri))
        author_account_after = Account.select().where(Account.did == author_account_before.did)[0]
        botaction = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        modaction = ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & (ModActions.did_user == author_account_before.did))\
            .order_by(ModActions.indexed_at.desc())[0]

    # first post entry should have been hidden; others should be untouched
    assert target_post_duplicates_after[0].hidden
    for target_post_after,target_post_before in zip(target_post_duplicates_after[1:], target_post_duplicates_before[1:]):
        assert target_post_after.hidden == target_post_before.hidden

    # everything else checked as normal
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
    '''Tests insufficient mod access failure case.
    
    For this case, there should be a BotAction entry created with all the usual details, 
    except authorized=False, and no ModAction entry created; the Post and Account entries 
    for the target post and its author, respectively, should be unchanged (with the post 
    still being hidden); and a post should be sent in reply to the instigating post to 
    indicate why the action has not been taken.
    '''
    # connect & collect and assertions
    with DBConnection():
        target_post_before = Post.select().where(Post.hidden)[-1]
        author_account_before = Account.select().where(Account.did == target_post_before.author)[0]
        moderator_account = Account.select().where(Account.mod_level < ModeratorHideCommand.level)[0] # get moderator of insufficient level
        latest_modaction_before = ModActions.select().order_by(ModActions.indexed_at.desc())[0]

    # make our hide command
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

    # post-act connect & collect and assertions
    call_signature = mock_client.send_post_call_signature
    parent_ref = hide_command.notification.parent_ref
    root_ref = hide_command.notification.root_ref
    assert call_signature["text"] == "Sorry, but you don't have the required permissions to run this command. Reason: Lacking required moderator level (2)"
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

    # make sure nothing happened (no modaction should have been added, and the target post should be in the same state)
    assert author_account_after.hidden_count == author_account_before.hidden_count
    assert target_post_after.hidden == target_post_before.hidden
    assert n_modactions == 0

    # botaction is normal, except for authorized being False
    assert botaction.indexed_at < datetime.utcnow()
    assert botaction.did == hide_command.notification.author.did
    assert botaction.type == hide_command.command
    assert botaction.stage == "complete"
    assert botaction.parent_uri == parent_ref.uri
    assert botaction.parent_cid == parent_ref.cid
    assert botaction.latest_uri == parent_ref.uri
    assert botaction.latest_cid == parent_ref.cid
    assert botaction.complete
    assert not botaction.authorized
    assert botaction.checked_at < datetime.utcnow()

def test_failure_author_not_signed_up(test_db_conn, mock_client):
    '''Tests failure case in which post author is not signed up to post in feeds.
    
    For this case, there should be a BotAction entry created with all the usual details, 
    and no ModAction entry created; the Post entry for the target post should be unchanged; 
    and a post should be sent in reply to the instigating post to indicate why the action 
    has not been taken.
    '''
    # create an author who will not be entered into the database, and a post by them that will not
    unregistered_author = testdb_account_entry(handle="Dasha", did="did:plc:DDDDDDDDDDDDDDDDDDDDDDDD")
    new_post = generate_testdb_post_by_author(text="astronomy is fantastic", author=unregistered_author)

    # connect & collect; and, add the post we just made (as far as I can tell, there is no way to 
    # return the entry just added from the insert().execute() call...would be nicer.......)
    with DBConnection() as conn:
        with conn.atomic():
            Post.insert(**asdict(new_post)).execute()
        target_post_before = Post.select().where(Post.author == unregistered_author.did)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(ModActions.indexed_at.desc())[0]

    # make our hide command
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

    # post-act connect & collect and assertions
    call_signature = mock_client.send_post_call_signature
    parent_ref = hide_command.notification.parent_ref
    root_ref = hide_command.notification.root_ref
    assert call_signature["text"] == "Unable to hide post: post author is not signed up to the feeds."
    assert call_signature["profile_identify"] is None
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)
    assert call_signature["embed"] == get_embed_info(None, None) # hide command calls astrobot.post.send_post embed=quote=None
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None

    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        botaction = BotActions.select().where(BotActions.parent_uri == parent_ref.uri)[0]
        n_modactions = \
            ModActions.select()\
            .where((ModActions.did_mod == moderator_account.did) & 
                   (ModActions.did_user == unregistered_author.did) & 
                   (ModActions.indexed_at > latest_modaction_before.indexed_at))\
            .count()

    # make sure nothing happened
    assert target_post_after.hidden == target_post_before.hidden
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

def test_failure_post_not_in_feeds(test_db_conn, mock_client):
    '''Tests failure case in which post is not in feeds.
    
    For this case, there should be a BotAction entry created with all the usual details, 
    and no ModAction entry created; the Account entry for the target post's author should 
    be unchanged; and a post sent in reply to the instigating post to indicate why the 
    action has not been taken.
    '''
    # connect & collect; don't need a post entry, or any specific author this time
    with DBConnection():
        author_account_before = Account.select()[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(ModActions.indexed_at.desc())[0]

    # we need to make a post with a registered author, and not put the post in the database
    unregistered_post = generate_testdb_post_by_author(
        text="geology is about rocks basically", 
        author=testdb_account_entry(handle=author_account_before.handle, did=author_account_before.did)
    )

    # make our hide command
    hide_reply_ref = build_reply_ref(         # we don't store root uri and cid in our Post table, leaving those as default values
        parent_ref_cid = unregistered_post.cid, 
        parent_ref_uri = unregistered_post.uri
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

    # post-act connect & collect and assertions
    call_signature = mock_client.send_post_call_signature
    parent_ref = hide_command.notification.parent_ref
    root_ref = hide_command.notification.root_ref
    assert call_signature["text"] == "Unable to hide post: post is not in feeds."
    assert call_signature["profile_identify"]is None
    assert call_signature["reply_to"] == get_reply_info(root_ref, parent_ref)
    assert call_signature["embed"] == get_embed_info(None, None) # hide command calls astrobot.post.send_post embed=quote=None
    assert call_signature["langs"] is None
    assert call_signature["facets"] is None

    with DBConnection():
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
    '''Tests failure case in which target post is already hidden.
    
    For this case, there should be a BotAction entry created with all the usual details, 
    and no ModAction entry created; the Post and Account entries for the target post and 
    its author should be unchanged (with the post hidden before and after command execution); 
    and a post should be sent in reply to the instigating post to indicate why the action 
    has not been taken.
    '''
    # connect & collect
    with DBConnection():
        target_post_before = Post.select().where(Post.hidden)[-1]
        author_account_before = Account.select().where(Account.did == target_post_before.author)[0]
        moderator_account = Account.select().where(Account.mod_level >= ModeratorHideCommand.level)[0] # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(ModActions.indexed_at.desc())[0]

    # make our hide command
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

    # post-act connect & collect and assertions
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

    # make sure nothing happened
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