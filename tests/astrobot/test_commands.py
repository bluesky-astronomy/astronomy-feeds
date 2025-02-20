import os
from datetime import datetime

from peewee import DatabaseProxy, SqliteDatabase
from atproto import Client, models

import astrofeed_lib.database # need to import this as a whole module to mock the database
from astrofeed_lib.database import BotActions, DBConnection
from astrofeed_lib.config import ASTROFEED_PRODUCTION

from astrobot.commands.joke import JokeCommand, jokes
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref, construct_strong_ref_main
from astrobot.config import HANDLE

# mock database infrastructure
mock_db = None
def get_mock_database() -> DatabaseProxy:
    '''replacement for actual database access'''
    # if we don't already have a database, create one
    global mock_db
    if(mock_db is None):
        # throwaway SQLite database
        db = SqliteDatabase("UNIT_TEST_MOCK_DB.db", autoconnect=False)

        # for consistency --- the rest of the code uses initialized proxies
        mock_db = DatabaseProxy()
        mock_db.initialize(db)

    return mock_db

# mock client class to replace the network-connected methods
class MockClient(Client):
    '''Replaces certain atproto.Client methods with offline-test appropriate alternatives'''
    def __init__(self, base_url = None, *args, **kwargs):
        super().__init__(base_url, *args, **kwargs)

        # instance variable to capture values that would be used to send post
        self.send_post_call_signature = dict()

    # instead of actually sending a post, store values that would be sent
    def send_post(self, text, profile_identify = None, reply_to = None, embed = None, langs = None, facets = None):
        self.send_post_call_signature.update({
            "text" : text, 
            "profile_identify" : profile_identify, 
            "reply_to" : reply_to, 
            "embed" : embed, 
            "langs" : langs, 
            "facets" : facets
            }
        )
        
        # need to return something with a CID and URI to not break the post.send_post method used by the joke command
        return construct_strong_ref_main()


def test_joke_unit():
    # just to be safe, make sure there's no risk of connecting to the live database
    if ASTROFEED_PRODUCTION: raise ConnectionRefusedError("Attempting to run offline unit test in production mode; aborting.")

    # create a joke command object with a mock notification
    joke_notification = build_notification("mention", record_text=f"@{HANDLE} joke", author_did="test_joke_unit")
    joke_command = JokeCommand(MentionNotification(joke_notification))

    # replace the database used by astrofeed lib with a mock database
    astrofeed_lib.database.get_database = get_mock_database
    astrofeed_lib.database.BotActions._meta.database = astrofeed_lib.database.get_database()
    with DBConnection() as conn:
        conn.create_tables([BotActions])

    # execute the command with a mock client
    mock_client = MockClient()
    joke_command.execute(mock_client)

    # extract quantities of interest and remove temporary files
    send_post_call_signature = mock_client.send_post_call_signature
    with DBConnection():
        test_entry = BotActions.select().where(BotActions.did == "test_joke_unit")[0]
    os.remove("UNIT_TEST_MOCK_DB.db")

    # check that send_post values and database entry are correct
    joke_strong_ref = models.create_strong_ref(joke_notification)
    joke_reply_ref = build_reply_ref(
        parent_ref_cid = joke_strong_ref.cid, 
        parent_ref_uri = joke_strong_ref.uri,
        root_ref_cid   = joke_strong_ref.cid, 
        root_ref_uri   = joke_strong_ref.uri
        )

    assert send_post_call_signature["text"] in jokes
    assert send_post_call_signature["profile_identify"] == None
    assert send_post_call_signature["reply_to"] == joke_reply_ref
    assert send_post_call_signature["embed"] == None
    assert send_post_call_signature["langs"] == None
    assert send_post_call_signature["facets"] == None

    assert test_entry.indexed_at < datetime.utcnow()          # better datetime test?
    assert test_entry.did == joke_notification.author.did
    assert test_entry.type == joke_command.command
    assert test_entry.stage == "complete"
    assert test_entry.parent_uri == joke_notification.uri
    assert test_entry.parent_cid == joke_notification.cid
    assert test_entry.latest_uri == joke_notification.uri
    assert test_entry.latest_cid == joke_notification.cid
    assert test_entry.complete == True
    assert test_entry.authorized == True
    assert test_entry.checked_at < datetime.utcnow()          # ditto above