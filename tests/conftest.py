import pytest
from datetime import datetime
from atproto import Client

from astrofeed_lib.database import proxy
from astrofeed_lib.config import ASTROFEED_PRODUCTION
from astrobot.generate_notification import construct_strong_ref_main
from tests.test_lib.test_database import build_test_db, populate_test_db, delete_test_db

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

@pytest.fixture(scope="function", autouse=True)
def check_production():
    '''check, for each test, that we have not entered production mode before running'''
    if ASTROFEED_PRODUCTION:
        raise ConnectionRefusedError("Attempting to run offline unit test in production mode; aborting.")

@pytest.fixture(scope="function")
def mock_client():
    '''gives each test it's own mock client'''
    return MockClient()

@pytest.fixture(scope="session")
def test_db_conn_session():
    '''creates and connects a PostgreSQL test database for the session'''
    # make new database and get connection
    now = datetime.now()
    test_database_name = f"test_db_{now.year}_{now.month}_{now.day}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}"
    db_conn = build_test_db(test_database_name)

    # redirect code to use new database
    database_prev = proxy.obj
    proxy.initialize(db_conn)

    # send connection
    yield proxy

    # cleanup; get rid of test database and schema file, and reset original database connection
    proxy.initialize(database_prev)
    delete_test_db(test_database_name)
    

@pytest.fixture(scope="function")
def test_db_conn(test_db_conn_session):
    '''manages the session database connection per test'''
    # freshly (re-)populate test database for the requesting test
    populate_test_db(test_db_conn_session, overwrite=True)

    # send session connection to the requesting test
    return test_db_conn_session