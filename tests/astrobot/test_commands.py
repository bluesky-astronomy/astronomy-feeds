from astrobot.commands.joke import JokeCommand, jokes
from astrobot.notifications import MentionNotification
from astrobot.generate_notification import build_notification, build_reply_ref, construct_strong_ref_main
from astrobot.config import HANDLE

from astrofeed_lib.config import ASTROFEED_PRODUCTION
from astrofeed_lib.database import BotActions, DBConnection

from atproto import Client, models

import os, pickle
from datetime import datetime

class DummyClient(Client):
    '''Replaces certain atproto.Client methods with offline-test appropriate alternatives'''
    # instead of actually sending an image/post, pickle all the values that would be used to send it
    def send_post(self, text, profile_identify = None, reply_to = None, embed = None, langs = None, facets = None):
        with open("send_post_call_signature.pickle","wb") as file:
            pickle.dump({"text" : text, 
                         "profile_identify" : profile_identify, 
                         "reply_to" : reply_to, 
                         "embed" : embed, 
                         "langs" : langs, 
                         "facets" : facets}, 
                         file=file)
        
        # need to return something with a CID and URI to not break the post.send_post method used by the joke command
        return construct_strong_ref_main()


def test_joke_unit():
    # until I can redirect database access, make sure we're not sending anything to live database
    if ASTROFEED_PRODUCTION: raise ConnectionRefusedError("Attempting to run offline unit test in production mode; aborting.")

    # create a joke command object with a dummy notification
    joke_notification = build_notification("mention", record_text=f"@{HANDLE} joke", author_did="test_joke_unit")
    joke_command = JokeCommand(MentionNotification(joke_notification))

    # execute the command with a dummy client
    dummy_client = DummyClient()
    joke_command.execute(dummy_client)

    # extract send_post argiuments and remove pickle file
    with open("send_post_call_signature.pickle","rb") as file:
        send_post_call_signature = pickle.load(file=file)
    os.remove("send_post_call_signature.pickle")

    # extract database entry, and remove from database
    with BotActions._meta.database as DBConnection:
        test_entry = BotActions.select().where(BotActions.did == "test_joke_unit")[0]
        test_entry.delete_instance()

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