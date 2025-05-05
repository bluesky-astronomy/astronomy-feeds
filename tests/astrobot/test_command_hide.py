from dataclasses import asdict

from astrofeed_lib.database import BotActions, ModActions, Post, Account
from astrofeed_lib.database import DBConnection

from astrobot.commands.moderation.hide import ModeratorHideCommand
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref
from astrobot.config import HANDLE
from tests.test_lib.test_database import (
    testdb_account_entry,
    testdb_post_entry,
    generate_testdb_post_by_author,
)
from tests.test_lib.test_util import (
    check_call_signature,
    check_botactions_entry,
    check_modactions_entry,
)

#
# utility functions
#


# cannot be a fixture, unfortunately, since each test needs to specify target post and author differently
def get_hide_command(
    target_post: Post | testdb_post_entry,
    moderator_account: Account | testdb_account_entry,
):
    """Builds a hide command object given a target post and moderator account."""
    # we don't store root uri and cid in our Post table, leaving those as default values
    hide_reply_ref = build_reply_ref(
        parent_ref_cid=target_post.cid, parent_ref_uri=target_post.uri
    )
    hide_notification = build_notification(
        "mention reply",
        record_text=f"@{HANDLE} hide",
        record_reply=hide_reply_ref,
        author_did=moderator_account.did,
    )
    return ModeratorHideCommand(MentionNotification(hide_notification))


#
# test functions
#


def test_success(test_db_conn, mock_client):
    """Tests standard expected success case.

    After command execution, the targeted post's Post entry should be marked hidden,
    and the author's Account entry should have its hidden_count field incremented by
    one; there should be a new BotAction and ModAction entry created, with appropriate
    information; and a Bluesky API call should have been made, to send a post to the
    instigating moderator informing them of action success.
    """
    # connect & collect
    with DBConnection():
        target_post_before = Post.select().where(~Post.hidden)[-1]
        author_account_before = Account.select().where(
            Account.did == target_post_before.author
        )[0]
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorHideCommand.level
        )[0]  # need a mod of high enough level

    # get our hide command
    hide_command = get_hide_command(target_post_before, moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_account_after = Account.select().where(
            Account.did == author_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        modaction = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == author_account_before.did)
            )
            .order_by(ModActions.indexed_at.desc())[0]
        )

    # checks; post should be hidden, and author hidden count incremented
    assert target_post_after.hidden
    assert author_account_after.hidden_count == author_account_before.hidden_count + 1

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Post hidden from feeds successfully.",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )
    check_modactions_entry(
        command=hide_command,
        did_user=hide_command.notification.notification.record.reply.parent.uri.replace(
            "at://", ""
        ).split("/")[0],
        modaction=modaction,
    )


def test_success_multiple_author_entries(test_db_conn, mock_client):
    """Tests success case in which target post's author has multiple entries in Account table.

    After command execution, the targeted post's Post entry should be marked hidden,
    and *only the first* Account entry for the author should have its hidden_count field
    incremented by one; there should be a new BotAction and ModAction entry created, with
    appropriate information; and a Bluesky API call should have been made, to send a post
    to the instigating moderator informing them of action success.
    """
    # connect & collect; and duplicate the post's author's Account entry if there aren't already duplicates
    with DBConnection() as conn:
        target_post_before = Post.select().where(~Post.hidden)[-1]
        author_account_select = Account.select().where(
            Account.did == target_post_before.author
        )
        if author_account_select.count() > 1:
            # database already has duplicate entries, (gotta) collect them all
            author_duplicates_before = list(author_account_select)
        else:
            # insert a duplicate and collect them
            author_account_dict = author_account_select.dicts()[0]
            author_account_dict["id"] = (
                Account.select().order_by(Account.id.desc())[0].id + 1
            )
            with conn.atomic():
                Account.insert(author_account_dict).execute()
            author_duplicates_before = list(
                Account.select().where(Account.did == target_post_before.author)
            )
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorHideCommand.level
        )[0]  # need a mod of high enough level

    # get our hide command
    hide_command = get_hide_command(target_post_before, moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_duplicates_after = list(
            Account.select().where(Account.did == author_duplicates_before[0].did)
        )
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        modaction = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == author_duplicates_before[0].did)
            )
            .order_by(ModActions.indexed_at.desc())[0]
        )

    # checks; first author entry should have been modified, others should be untouched
    assert (
        author_duplicates_after[0].hidden_count
        == author_duplicates_before[0].hidden_count + 1
    )
    for author_after, author_before in zip(
        author_duplicates_after[1:], author_duplicates_before[1:]
    ):
        assert author_after.hidden_count == author_before.hidden_count

    # everything else checked as normal
    assert target_post_after.hidden

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Post hidden from feeds successfully.",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )
    check_modactions_entry(
        command=hide_command,
        did_user=hide_command.notification.notification.record.reply.parent.uri.replace(
            "at://", ""
        ).split("/")[0],
        modaction=modaction,
    )


def test_success_multiple_post_entries(test_db_conn, mock_client):
    """Tests success case in which target post has multiple entries in Post table.

    After command execution, *only the first* Post entry for the targeted post should
    be marked hidden, and the author's Account entry should have its hidden_count field
    incremented by one; there should be a new BotAction and ModAction entry created,
    with appropriate information; and a Bluesky API call should have been made, to send
    a post to the instigating moderator informing them of action success.
    """
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
            target_post_duplicates_before = list(
                Post.select().where(Post.uri == target_post_initial.uri)
            )

        author_account_before = Account.select().where(
            Account.did == target_post_duplicates_before[0].author
        )[0]
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorHideCommand.level
        )[0]  # need a mod of high enough level

    # get our hide command
    hide_command = get_hide_command(target_post_duplicates_before[0], moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_post_duplicates_after = list(
            Post.select().where(Post.uri == target_post_duplicates_before[0].uri)
        )
        author_account_after = Account.select().where(
            Account.did == author_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        modaction = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == author_account_before.did)
            )
            .order_by(ModActions.indexed_at.desc())[0]
        )

    # checks; first post entry should have been hidden, others should be untouched
    assert target_post_duplicates_after[0].hidden
    for target_post_after, target_post_before in zip(
        target_post_duplicates_after[1:], target_post_duplicates_before[1:]
    ):
        assert target_post_after.hidden == target_post_before.hidden

    # everything else checked as normal
    assert author_account_after.hidden_count == author_account_before.hidden_count + 1

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Post hidden from feeds successfully.",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )
    check_modactions_entry(
        command=hide_command,
        did_user=hide_command.notification.notification.record.reply.parent.uri.replace(
            "at://", ""
        ).split("/")[0],
        modaction=modaction,
    )


def test_failure_insufficient_mod_level(test_db_conn, mock_client):
    """Tests failure case in which instigating account has insufficient mod access.

    In this case, no modification should be made to any Post or Account
    entry; no ModAction entry should be created, and a BotAction entry
    should be created with authorized=False; and a Bluesky API call should
    be made to send a post to the instigating account indicating action
    failure, and the reason for the failure.
    """
    # connect & collect
    with DBConnection():
        target_post_before = Post.select().where(Post.hidden)[-1]
        author_account_before = Account.select().where(
            Account.did == target_post_before.author
        )[0]
        moderator_account = Account.select().where(
            Account.mod_level < ModeratorHideCommand.level
        )[0]  # get moderator of insufficient level
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # get our hide command
    hide_command = get_hide_command(target_post_before, moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_account_after = Account.select().where(
            Account.did == author_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == author_account_before.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks; in this case, no mod action should have been taken
    assert author_account_after.hidden_count == author_account_before.hidden_count
    assert target_post_after.hidden == target_post_before.hidden
    assert n_modactions == 0

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Sorry, but you don't have the required permissions to run this command. Reason: Lacking required moderator level (2)",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )


def test_failure_author_not_signed_up(test_db_conn, mock_client):
    """Tests failure case in which post author is not signed up to post in feeds.

    In this case, no modification should be made to any Post or Account
    entry; no ModAction entry should be created, and a BotAction entry
    should be created as usual; and a Bluesky API call should be made to
    send a post to the instigating account indicating action failure, and
    the reason for the failure.
    """
    # create an author who will not be entered into the database, and a post by them that will not
    unregistered_author = testdb_account_entry(
        handle="Dasha", did="did:plc:DDDDDDDDDDDDDDDDDDDDDDDD"
    )
    new_post = generate_testdb_post_by_author(
        text="astronomy is fantastic", author=unregistered_author
    )

    # connect & collect; and, add the post we just made (as far as I can tell, there is no way to
    # return the entry just added from the insert().execute() call...would be nicer.......)
    with DBConnection() as conn:
        with conn.atomic():
            Post.insert(**asdict(new_post)).execute()
        target_post_before = Post.select().where(
            Post.author == unregistered_author.did
        )[0]
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorHideCommand.level
        )[0]  # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # get our hide command
    hide_command = get_hide_command(target_post_before, moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == unregistered_author.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks; in this case, no mod action should have been taken
    assert target_post_after.hidden == target_post_before.hidden
    assert n_modactions == 0

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Unable to hide post: post author is not signed up to the feeds.",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )


def test_failure_post_not_in_feeds(test_db_conn, mock_client):
    """Tests failure case in which post is not in feeds.

    In this case, no modification should be made to any Post or Account
    entry; no ModAction entry should be created, and a BotAction entry
    should be created as usual; and a Bluesky API call should be made to
    send a post to the instigating account indicating action failure, and
    the reason for the failure.
    """
    # connect & collect; don't need a post entry, or any specific author this time
    with DBConnection():
        author_account_before = Account.select()[0]
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorHideCommand.level
        )[0]  # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # we need to make a post with a registered author, and not put the post in the database
    unregistered_post = generate_testdb_post_by_author(
        text="geology is about rocks basically",
        author=testdb_account_entry(
            handle=author_account_before.handle, did=author_account_before.did
        ),
    )

    # get our hide command
    hide_command = get_hide_command(unregistered_post, moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        author_account_after = Account.select().where(
            Account.did == author_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == author_account_before.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks; in this case, no mod action should have been taken
    assert author_account_after.hidden_count == author_account_before.hidden_count
    assert n_modactions == 0

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Unable to hide post: post is not in feeds.",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )


def test_failure_post_already_hidden(test_db_conn, mock_client):
    """Tests failure case in which target post is already hidden.

    In this case, no modification should be made to any Post or Account
    entry (with the Post entry remaining hidden); no ModAction entry should
    be created, and a BotAction entry should be created as usual; and a
    Bluesky API call should be made to send a post to the instigating account
    indicating action failure, and the reason for the failure.
    """
    # connect & collect
    with DBConnection():
        target_post_before = Post.select().where(Post.hidden)[-1]
        author_account_before = Account.select().where(
            Account.did == target_post_before.author
        )[0]
        moderator_account = Account.select().where(
            Account.mod_level >= ModeratorHideCommand.level
        )[0]  # need a mod of high enough level
        latest_modaction_before = ModActions.select().order_by(
            ModActions.indexed_at.desc()
        )[0]

    # get our hide command
    hide_command = get_hide_command(target_post_before, moderator_account)

    # act
    hide_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        target_post_after = Post.select().where(Post.uri == target_post_before.uri)[0]
        author_account_after = Account.select().where(
            Account.did == author_account_before.did
        )[0]
        botaction = BotActions.select().where(
            BotActions.parent_uri == hide_command.notification.parent_ref.uri
        )[0]
        n_modactions = (
            ModActions.select()
            .where(
                (ModActions.did_mod == moderator_account.did)
                & (ModActions.did_user == author_account_before.did)
                & (ModActions.indexed_at > latest_modaction_before.indexed_at)
            )
            .count()
        )

    # checks; in this case, no mod action should have been taken
    assert author_account_after.hidden_count == author_account_before.hidden_count
    assert target_post_after.hidden
    assert n_modactions == 0

    check_call_signature(
        command=hide_command,
        mock_client=mock_client,
        text="Unable to hide post: post already hidden.",
    )
    check_botactions_entry(
        command=hide_command,
        botaction=botaction,
    )
