"""Tools for handling lists of accounts and working with Bluesky DIDs etc."""
from .database import db, Account
from .config import QUERY_INTERVAL, HANDLE, PASSWORD
from atproto import AsyncClient
import logging
import time
import asyncio


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AccountQuery:
    def __init__(self, with_database_closing=False, flags=None) -> None:
        """Generic refreshing account list. Will return all accounts that have flags
        matching the defined 'flags' parameter.
        """
        self.accounts = None
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
        self.query_database()
        return self.accounts  # type: ignore (because pylance is a silly thing here. this should always be a set)


class CachedAccountQuery(AccountQuery):
    def __init__(self, with_database_closing=False, flags=None, query_interval: int = 60 * 60 * 24) -> None:
        """Generic refreshing account list. Will return all accounts that have flags
        matching the defined 'flags' parameter.
        """
        super.__init__(with_database_closing=with_database_closing, flags=flags)
        self.query_interval = query_interval
        self.last_query_time = time.time()
        
    def get_accounts(self) -> set:
        is_overdue = time.time() - self.last_query_time > QUERY_INTERVAL
        if is_overdue or self.accounts is None:
            self.query_database()
            self.last_query_time = time.time()
        return self.accounts  # type: ignore (because pylance is a silly thing here. this should always be a set)


async def fetch_handle(client, handle):
    """Fetches DIDs - NOT handles!"""
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


async def fetch_handle_from_did_async(client, did):
    try: 
        response = await client.com.atproto.repo.describe_repo(params={'repo': did})
        logger.info(f"Found handle for {did}")
        return response
    except Exception as e:
        logger.warn(f"Unable to fetch a handle for account name {did}: {e}")
    return {'handle': None}


async def fetch_handles_async(accounts_to_query):
    # Asynchronously query all of the handles
    logger.info(f"-> looking up account handles for the following DIDs:\n{accounts_to_query}")

    client = AsyncClient()
    await client.login(HANDLE, PASSWORD)

    tasks = [fetch_handle_from_did_async(client, handle) for handle in accounts_to_query]
    responses = await asyncio.gather(*tasks)
    logger.info(responses)

    return {did: response['handle'] for did, response in zip(accounts_to_query, responses) if response is not None}


def fetch_handles(account_dids):
    return asyncio.run(fetch_handles_async(account_dids))
