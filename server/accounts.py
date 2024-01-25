"""Legacy code for handling account-related things. Will be migrated to another repo
in a future release.
"""
import pandas as pd
import time
import logging
from astrofeed_lib.config import SHEET_LINK, QUERY_INTERVAL
from astrofeed_lib.accounts import fetch_dids
from astrofeed_lib.database import Account, db
import warnings

warnings.warn(
    DeprecationWarning(
        "This accounts service will be migrated to a separate repo in a future release,"
        " and/or replaced outright."
    )
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def query_google_sheets():
    """This is so fucking janky lmao"""
    logger.info("-> fetching Google sheet")
    all_accounts = pd.read_csv(SHEET_LINK, usecols=["time", "name", "id", "valid"])

    # Sanitise the valid column into a boolean only (it can be blank otherwise)
    all_accounts["valid"] = all_accounts["valid"] is True
    return all_accounts


def sanitise_handles(all_accounts):
    """Sanitises handle names in all_accounts to remove common encountered errors with incorrect account names."""
    all_accounts["name"] = [x.strip() for x in all_accounts["name"]]


def refresh_valid_accounts(limit=50):
    """Service that looks up current list of valid accounts, adding new DIDs to the database when new accounts are
    found, in addition to updating the validity of accounts based on the looked up source.

    Conceptually, this means DIDs are queried and posts are indexed well before a user may be marked as valid, which
    allows for the feed to be populated with their recent skeets immediately when their validity changes.
    """
    while True:
        logger.info("Refreshing current list of valid accounts.")

        # Grab the latest account data from Google Sheets
        all_accounts = query_google_sheets().dropna(subset=["name", "id", "valid"])
        sanitise_handles(all_accounts)

        # Open the database connection
        if db.is_closed():
            db.connect()

        # Work out which accounts are not in the account database
        existing_handles = [account.submission_id for account in Account.select()]  # noqa: F841
        new_accounts = (
            all_accounts.query("id not in @existing_handles").reset_index().loc[:limit]
        )

        # Add any new accounts
        if len(new_accounts) > 0:
            logger.info(f"-> Found {len(new_accounts)} new accounts!")

            # Grab DIDs for these new accounts
            new_did_mapping = fetch_dids(new_accounts["name"].tolist())

            # Add everyone to the db!
            with db.atomic():
                for i, an_account in new_accounts.iterrows():
                    if (did := new_did_mapping[an_account["name"]]) is not None:
                        Account.create(
                            handle=an_account["name"],
                            submission_id=an_account["id"],
                            did=did,
                            is_valid=an_account["valid"],
                            feed_all=True,
                        )

        # Update the validity status of existing accounts
        # Todo: can this be written in a less janky way
        with db.atomic():
            number_validated = (
                Account.update(is_valid=True)
                .where(
                    Account.submission_id << all_accounts.query("valid")["id"].tolist()
                )
                .execute()
            )
            number_unvalidated = (
                Account.update(is_valid=False)
                .where(
                    Account.submission_id
                    << all_accounts.query("not valid")["id"].tolist()
                )
                .execute()
            )
        logger.info(
            f"-> Marked {number_validated} accounts as valid and {number_unvalidated} as now invalid."
        )

        # Close the database connection, since it should be a little while until we interact with it again.
        if not db.is_closed():
            db.close()

        # Sleep! (Since downloading the .csv is relatively expensive, it's better to not do this too often.)
        # Todo: stopping criteria here is janky as fuck, fix this shit
        i = 0
        while i < QUERY_INTERVAL:
            time.sleep(5)
            i += 5
