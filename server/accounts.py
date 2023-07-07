import pandas as pd
import time
import asyncio
import logging
from .config import HANDLE, PASSWORD, SHEET_LINK, QUERY_INTERVAL
from atproto import AsyncClient
from .database import Account, db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)





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


def query_google_sheets():
    """This is so fucking janky lmao"""
    logger.info("-> fetching Google sheet")
    all_accounts = pd.read_csv(SHEET_LINK, usecols=["time", "name", "id", "valid"])
    
    # Sanitise the valid column into a boolean only (it can be blank otherwise)
    all_accounts['valid'] = all_accounts['valid'] == True
    return all_accounts
    

def refresh_valid_accounts(stream_stop_event=None, limit=50):
    while True:
        logger.info("Refreshing current list of valid accounts.")

        # Grab the df
        all_accounts = query_google_sheets()

        # Work out which accounts are not in the account database
        existing_handles = [account.submission_id for account in Account.select()]
        new_accounts = all_accounts.query("id not in @existing_handles").reset_index().loc[:limit]

        # Add any new accounts
        if len(new_accounts) > 0:
            logger.info(f"-> Found {len(new_accounts)} new accounts!")

            # Grab DIDs for these new accounts
            new_did_mapping = fetch_dids(new_accounts['name'].tolist())

            # Add everyone to the db!
            with db.atomic():
                for i, an_account in new_accounts.iterrows():
                    if (did := new_did_mapping[an_account['name']]) is not None:
                        Account.create(
                            handle=an_account['name'],
                            submission_id=an_account['id'],
                            did=did,
                            is_valid=an_account['valid'],
                            feed_all=True
                        )

        # Update the validity status of existing accounts
        # Todo: can this be written in a less janky way
        with db.atomic():
            number_validated = (Account
            .update(is_valid=True)
            .where(Account.submission_id << all_accounts.query("valid")['id'].tolist())
            .execute()
            )
            number_unvalidated = (Account
            .update(is_valid=False)
            .where(Account.submission_id << all_accounts.query("not valid")['id'].tolist())
            .execute()
            )
        logger.info(f"-> Marked {number_validated} accounts as valid and {number_unvalidated} as now invalid.")
        
        
        # Sleep! (Since downloading the .csv is relatively expensive, it's better to not do this too often.)
        # Todo: stopping criteria here is janky as fuck, fix this shit
        i = 0
        while i < QUERY_INTERVAL:
            if stream_stop_event and stream_stop_event.is_set():
                return
            time.sleep(1)
            i += 1
