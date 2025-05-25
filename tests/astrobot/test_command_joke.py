from astrofeed_lib.database import BotActions, Account
from astrofeed_lib.database import DBConnection

from astrobot.commands.joke import JokeCommand, jokes
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification
from astrobot.config import HANDLE

from tests.test_lib.test_database import testdb_account_entry
from tests.test_lib.test_util import check_call_signature, check_botactions_entry

#
# utility functions
#


# cannot be a fixture, unfortunately, since each test needs to specify target post and author differently
def get_joke_command(
    requesting_user: Account | testdb_account_entry,
):
    """Builds a hide command object given a target post and moderator account."""
    # we don't store root uri and cid in our Post table, leaving those as default values
    joke_notification = build_notification(
        "mention", record_text=f"@{HANDLE} joke", author_did=requesting_user.did
    )
    return JokeCommand(MentionNotification(joke_notification))


#
# test functions
#


def test_joke(test_db_conn, mock_client):
    # connect & collect
    with DBConnection():
        requesting_account = Account.select()[0]

    # get our joke command
    joke_command = get_joke_command(requesting_user=requesting_account)

    # act
    joke_command.execute(mock_client)

    # post-act connect & collect
    with DBConnection():
        botaction = BotActions.select().where(
            BotActions.parent_uri == joke_command.notification.parent_ref.uri
        )[0]

    # checks
    check_call_signature(
        command=joke_command,
        mock_client=mock_client,
        text=jokes,
    )
    check_botactions_entry(
        command=joke_command,
        botaction=botaction,
    )
