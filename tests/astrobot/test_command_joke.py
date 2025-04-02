from datetime import datetime
from atproto import models

from astrofeed_lib.database import BotActions
from astrofeed_lib.database import DBConnection
from astrofeed_lib.config import ASTROFEED_PRODUCTION

from astrobot.commands.joke import JokeCommand, jokes
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref
from astrobot.config import HANDLE

def test_joke(test_db_conn, mock_client):
    # just to be safe, make sure there's no risk of connecting to the live database
    if ASTROFEED_PRODUCTION:
        raise ConnectionRefusedError("Attempting to run offline unit test in production mode; aborting.")

    # create a joke command object with a mock notification
    joke_notification = build_notification("mention", record_text=f"@{HANDLE} joke", author_did="test_joke_unit")
    joke_command = JokeCommand(MentionNotification(joke_notification))

    # act
    joke_command.execute(mock_client)

    # extract quantities of interest and make assertions
    send_post_call_signature = mock_client.send_post_call_signature
    joke_strong_ref = models.create_strong_ref(joke_notification)
    joke_reply_ref = build_reply_ref(
        parent_ref_cid = joke_strong_ref.cid, 
        parent_ref_uri = joke_strong_ref.uri,
        root_ref_cid   = joke_strong_ref.cid, 
        root_ref_uri   = joke_strong_ref.uri
        )
    assert send_post_call_signature["text"] in jokes
    assert send_post_call_signature["profile_identify"] is None
    assert send_post_call_signature["reply_to"] == joke_reply_ref
    assert send_post_call_signature["embed"] is None
    assert send_post_call_signature["langs"] is None
    assert send_post_call_signature["facets"] is None

    with DBConnection(): # seems to be necessary here --- joke command execution must close connection?
        test_entry = BotActions.select().where(BotActions.did == "test_joke_unit")[0]
    assert test_entry.indexed_at < datetime.utcnow()          # better datetime test?
    assert test_entry.did == joke_notification.author.did
    assert test_entry.type == joke_command.command
    assert test_entry.stage == "complete"
    assert test_entry.parent_uri == joke_notification.uri
    assert test_entry.parent_cid == joke_notification.cid
    assert test_entry.latest_uri == joke_notification.uri
    assert test_entry.latest_cid == joke_notification.cid
    assert test_entry.complete
    assert test_entry.authorized
    assert test_entry.checked_at < datetime.utcnow()          # ditto above