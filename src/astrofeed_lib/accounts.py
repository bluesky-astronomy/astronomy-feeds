"""Tools for handling lists of accounts and working with Bluesky DIDs etc."""
from .database import db, Account
from .config import QUERY_INTERVAL, HANDLE, PASSWORD
from atproto import AsyncClient
import logging
import time
import asyncio


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AccountList:
    def __init__(self, with_database_closing=False, flags=None) -> None:
        """Generic refreshing account list. Tries to reduce number of required query operations!"""
        self.accounts = None
        self.last_query_time = time.time()
        self.flags = flags
        if with_database_closing:
            self.query_database = self.query_database_with_closing
        else:
            self.query_database = self.query_database_without_closing

    def query_database_without_closing(self) -> None:
        db.connect(reuse_if_open=True)
        self.accounts = self.account_query()

    def query_database_with_closing(self) -> None:
        db.connect(reuse_if_open=True)
        self.accounts = self.account_query()
        db.close()

    def account_query(self):
        """Intended to be overwritten! Should return a set of accounts."""
        query = Account.select()
        if self.flags is not None:
            query = query.where(*self.flags)
        return {account.did for account in query}
        

    def get_accounts(self) -> set:
        is_overdue = time.time() - self.last_query_time > QUERY_INTERVAL
        if is_overdue or self.accounts is None:
            self.query_database()
            self.last_query_time = time.time()
        return self.accounts


async def fetch_handle(client, handle):
    try: 
        response = await client.com.atproto.identity.resolve_handle(params={'handle': handle})
        logger.info(f"Found DID for {handle}")
        return response
    except Exception as e:
        logger.warn(f"Unable to fetch a DID for account name {handle}: {e}")
    return {'did': None}


async def fetch_dids_async(accounts_to_query):
    # Asynchronously query all of the handles
    logger.info(f"-> looking up account DIDs for the following handles:\n{accounts_to_query}")

    client = AsyncClient()
    await client.login(HANDLE, PASSWORD)

    tasks = [fetch_handle(client, handle) for handle in accounts_to_query]
    responses = await asyncio.gather(*tasks)
    logger.info(responses)

    return {handle: response['did'] for handle, response in zip(accounts_to_query, responses) if response is not None}


def fetch_dids(account_names):
    return asyncio.run(fetch_dids_async(account_names))