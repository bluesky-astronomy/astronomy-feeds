import os
import pytest
from datetime import datetime
from atproto import Client
from peewee import SqliteDatabase

from astrofeed_lib.database import proxy
from astrobot.generate_notification import construct_strong_ref_main
from test_lib.test_database import build_test_db

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

@pytest.fixture(scope="function")
def mock_client():
    '''gives each test it's own mock client'''
    return MockClient()

@pytest.fixture(scope="function")
def test_db_conn():
    '''creates and connects an SQLite test database for the session'''
    # make new database and get connection
    database_name = f"test_db_{datetime.now()}.db"
    build_test_db(database_name=database_name)
    db_conn = SqliteDatabase(database_name, autoconnect=False)

    # redirect code to use new database
    database_prev = proxy.obj
    proxy.initialize(db_conn)
    #setup_connection(proxy)

    # send connection
    yield proxy

    # cleanup
    #teardown_connection(proxy)
    os.remove(database_name)
    proxy.initialize(database_prev)