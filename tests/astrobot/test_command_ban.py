#from dataclasses import asdict

from astrofeed_lib.database import BotActions, ModActions, Account
from astrofeed_lib.database import DBConnection

from astrobot.commands.moderation.ban import ModeratorBanCommand
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification
from astrobot.config import HANDLE
from tests.test_lib.test_database import (
    testdb_account_entry,
)
from tests.test_lib.test_util import check_call_signature, check_botactions_entry, check_modactions_entry


#
# utility functions
#


# cannot be fixtures, unfortunately, since each test needs to specify target post and author differently

def get_ban_command(
    target_user: Account | testdb_account_entry,
    moderator_account: Account | testdb_account_entry,
):
    """Builds a ban command object given a target user and a moderator account."""
    ban_notification = build_notification(
        "mention",
        record_text=f"@{HANDLE} ban {target_user.handle}",
        author_did=moderator_account.did,
    )
    return ModeratorBanCommand(MentionNotification(ban_notification))


#
# test functions
#


def test_success(test_db_conn, mock_client, mock_idresolver):
    """Tests success case in which ban command explicitly named (by handle) user to ban

    After command execution, the targeted user's Account entry (the one associated with 
    the replied-to post) should have banned=True, and have its banned_count field 
    incremented by one; there should be a new BotAction and ModAction entry created, 
    with appropriate information; and a Bluesky API call should have been made, to send 
    a post to the instigating moderator informing them of action success.
    """
    # connect & collect
    with DBConnection():
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorBanCommand.level
        )[0]  # need a mod of high enough level
        target_account_before = Account.select().where(Account.did != moderator_account.did)[0]

    # set up successful mock ID resolution
    mock_idresolver.add_mapping(target_account_before.handle, target_account_before.did)

    # get our ban command
    ban_command = get_ban_command(target_account_before, moderator_account)

    # act
    ban_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_account_after = Account.select().where(
            Account.did == target_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == ban_command.notification.parent_ref.uri
        )[0]
        modaction = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == target_account_before.did)
            )
            .order_by(ModActions.indexed_at.desc())[0]
        )

    # checks
    assert target_account_after.is_banned
    assert target_account_after.banned_count == target_account_before.banned_count + 1

    # do posts get hidden automatically when a user is banned?

    check_call_signature(
        command=ban_command,
        mock_client=mock_client,
        text="User banned from feeds successfully.",
    )
    check_botactions_entry(
        command=ban_command, 
        botaction=botaction,
    )
    check_modactions_entry(
        command=ban_command, 
        did_user=target_account_before.did, 
        modaction=modaction,
    )

def test_success_multiple_author_entries(test_db_conn, mock_client, mock_idresolver):
    """Tests success case in which user to ban has multiple entries in Account table

    Note: for this and futures cases, it doesn't matter whether we take the "reply" or
    "mention" path, as beyond the reply vs mention decision point, they will both make 
    the same function call.
    
    After command execution, every one of the Account entries associated with the target 
    user should have banned=True, and they should *all* have their banned_count field 
    set to one higher than the banned_count of whichever entry had the maximum 
    banned_count before command execution; there should be a new BotAction and ModAction 
    entry created, with appropriate information; and a Bluesky API call should have been 
    made, to send a post to the instigating moderator informing them of action success.
    """
    # connect & collect
    with DBConnection() as conn:
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorBanCommand.level
        )[0]  # need a high enough level
        target_account_before = Account.select().where(Account.did != moderator_account.did)[0]

        # Need to duplicate our target author a few times, with specific properties:
        #   * we want some duplicate entries to already be banned, and some not; 
        #   * and we want them to have different banned_counts
        # This will allow us to test that all entries, regardless of initial state, 
        # are banned at the end; and that they all get the correct banned_count
        target_account_dict = target_account_before.__dict__["__data__"]
        max_account_id = Account.select().order_by(Account.id.desc())[0].id
        base_banned_count = target_account_dict["banned_count"]
        for i in [1, 2]:
            target_account_dict["id"] = max_account_id + i # guarantee unique id per entry
            target_account_dict["is_banned"] = i%2 == 0 # one already banned, one not
            target_account_dict["banned_count"] = base_banned_count + i # three different banned counts
            with conn.atomic():
                Account.insert(target_account_dict).execute()
        target_duplicates_before = list(
            Account.select().where(Account.did == target_account_before.did)
        )
        max_banned_count_before = max([account.banned_count for account in target_duplicates_before])


    # set up successful mock ID resolution
    mock_idresolver.add_mapping(target_account_before.handle, target_account_before.did)

    # get our ban command
    ban_command = get_ban_command(target_account_before, moderator_account)

    # act
    ban_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_duplicates_after = list(
            Account.select().where(Account.did == target_account_before.did)
        )
        botaction = BotActions.select().where(
            BotActions.parent_uri == ban_command.notification.parent_ref.uri
        )[0]
        modaction = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == target_account_before.did)
            )
            .order_by(ModActions.indexed_at.desc())[0]
        )

    # checks
    for account in target_duplicates_after:
        assert account.is_banned
        assert account.banned_count == max_banned_count_before + 1

    # do posts get hidden automatically when a user is banned?

    check_call_signature(
        command=ban_command,
        mock_client=mock_client,
        text="User banned from feeds successfully.",
    )
    check_botactions_entry(
        command=ban_command, 
        botaction=botaction,
    )
    check_modactions_entry(
        command=ban_command, 
        did_user=target_account_before.did, 
        modaction=modaction,
    )



def test_failure_insufficient_mod_level(test_db_conn, mock_client, mock_idresolver):
    """Tests failure case in which instigating account has insufficient mod access.

    In this case, no modification should be made to any Account entry; no ModAction
    entry should be created, and a BotAction entry should be created with 
    authorized=False; and a Bluesky API call should be made to send a post to the 
    instigating account indicating action failure, and the reason for the failure.
    """
    # connect & collect
    with DBConnection():
        moderator_account = Account.select().where(
            Account.mod_level < ModeratorBanCommand.level
        )[0]  # need a mod of too low a level
        target_account_before = Account.select().where(Account.did != moderator_account.did)[0]
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # set up successful mock ID resolution
    mock_idresolver.add_mapping(target_account_before.handle, target_account_before.did)

    # get our ban command
    ban_command = get_ban_command(target_account_before, moderator_account)

    # act
    ban_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_account_after = Account.select().where(
            Account.did == target_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == ban_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == target_account_before.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks
    assert not target_account_after.is_banned
    assert target_account_after.banned_count == target_account_before.banned_count
    assert n_modactions == 0

    check_call_signature(
        command=ban_command,
        mock_client=mock_client,
        text=f"Sorry, but you don't have the required permissions to run this command. Reason: Lacking required moderator level ({ban_command.level})",
    )
    check_botactions_entry(
        command=ban_command, 
        botaction=botaction,
    )


def test_failure_cannot_resolve_handle_to_ban(test_db_conn, mock_client, mock_idresolver):
    """Tests failure case in which the handle specified to ban in a mention cannot be resolved
    
    In this case, no modification should be made to any Account entry; no ModAction
    entry should be created, and a BotAction entry should be created as usual; and 
    a Bluesky API call should be made to send a post to the instigating account 
    indicating action failure, and the reason for the failure.
    """
    with DBConnection():
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorBanCommand.level
        )[0]  # need a mod of high enough level
        target_account_before = Account.select().where(Account.did != moderator_account.did)[0]
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # make sure that the handle will not resolve succesfully
    mock_idresolver.remove_mapping_by_handle(target_account_before.handle)

    # get our ban command
    ban_command = get_ban_command(target_account_before, moderator_account)

    # act
    ban_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_account_after = Account.select().where(
            Account.did == target_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == ban_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == target_account_before.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks
    assert target_account_after.is_banned == target_account_before.is_banned
    assert target_account_after.banned_count == target_account_before.banned_count
    assert n_modactions == 0

    # do posts get hidden automatically when a user is banned?

    check_call_signature(
        command=ban_command,
        mock_client=mock_client,
        text=f"Unable to execute ban; not able to resolve given user handle \"{ban_command.notification.words[1]}\"",
    )
    check_botactions_entry(
        command=ban_command, 
        botaction=botaction,
    )

def test_failure_user_not_signed_up(test_db_conn, mock_client, mock_idresolver):
    """Tests failure case in which target user is not signed up to post in feeds.
    
    In this case, no modification should be made to any Account entry; no ModAction
    entry should be created, and a BotAction entry should be created as usual; and 
    a Bluesky API call should be made to send a post to the instigating account 
    indicating action failure, and the reason for the failure.
    """
    # create an author who will not be entered into the database, and a post by them that will not
    unregistered_user = testdb_account_entry(
        handle="Dasha", did="did:plc:DDDDDDDDDDDDDDDDDDDDDDDD"
    )

    # connect & collect
    with DBConnection():
        moderator_account = Account.select().where(
            Account.mod_level > ModeratorBanCommand.level
        )[0]  # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # set up successful mock ID resolution
    mock_idresolver.add_mapping(unregistered_user.handle, unregistered_user.did)

    # get our ban command
    ban_command = get_ban_command(unregistered_user, moderator_account)

    # act
    ban_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        botaction = BotActions.select().where(
            BotActions.parent_uri == ban_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == unregistered_user.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks
    assert n_modactions == 0

    check_call_signature(
        command=ban_command,
        mock_client=mock_client,
        text="Unable to ban user: user is not signed up to the feeds.",
    )
    check_botactions_entry(
        command=ban_command, 
        botaction=botaction,
    )


def test_failure_user_already_banned(test_db_conn, mock_client, mock_idresolver):
    """Tests failure case in which target user is already banned from feeds.
    
    In this case, no modification should be made to any Account entry (with all 
    Account entries for target user remaining banned); no ModAction entry should 
    be created, and a BotAction entry should be created as usual; and a Bluesky 
    API call should be made to send a post to the instigating account indicating 
    action failure, and the reason for the failure.
    """
    # connect & collect
    with DBConnection():
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorBanCommand.level
        )[0]  # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

        # modify our author account to make it banned already
        target_account_before = Account.select().where(Account.did != moderator_account.did)[0]
        target_account_before.is_banned = True
        target_account_before.banned_count = 1
        target_account_before.save()

    # set up successful mock ID resolution
    mock_idresolver.add_mapping(target_account_before.handle, target_account_before.did)

    # get our ban command
    ban_command = get_ban_command(target_account_before, moderator_account)

    # act
    ban_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_account_after = Account.select().where(
            Account.did == target_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == ban_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == target_account_before.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks
    assert target_account_after.is_banned
    assert target_account_after.banned_count == target_account_before.banned_count
    assert n_modactions == 0

    # do posts get hidden automatically when a user is banned?

    check_call_signature(
        command=ban_command,
        mock_client=mock_client,
        text="Unable to ban user: user already banned.",
    )
    check_botactions_entry(
        command=ban_command, 
        botaction=botaction,
    )