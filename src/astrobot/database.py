"""A collection of all database actions for things the bot needs to do."""

from datetime import datetime, timedelta, timezone
import warnings

import peewee
from astrofeed_lib.database import BotActions, ModActions, Account, get_database, setup_connection, teardown_connection
from icecream import ic

# set up icecream
ic.configureOutput(includeContext=True)

REQUIRED_BOT_ACTION_FIELDS = [
    "did",
    "type",
    "stage",
    "parent_uri",
    "parent_cid",
    "latest_uri",
    "latest_cid",
    "complete",
]


def fetch_account_entry_for_did(did):
    """Checks to see if a user is already signed up to the feeds."""
    # db.connect(reuse_if_open=True)
    setup_connection(get_database())
    retval = [x for x in Account.select().where(Account.did == did)]
    teardown_connection(get_database())
    return retval


def new_bot_action(
    command,
    stage: str = "complete",
    latest_uri: None | str = None,
    latest_cid: None | str = None,
    authorized: bool = True,
):
    """Save a new bot action to the database. Defaults to stage='complete', which marks
    the action as already completed in the database.
    """
    complete = False
    if stage == "complete":
        complete = True

    if latest_uri is None:
        latest_uri = command.notification.parent_ref.uri
    if latest_cid is None:
        latest_cid = command.notification.parent_ref.uri

    #db.connect(reuse_if_open=True)
    setup_connection(get_database())
    with get_database().atomic():
        BotActions.create(
            did=command.notification.author.did,
            type=command.command,
            stage=stage,
            parent_uri=command.notification.parent_ref.uri,  # This is a mis-nomer, should be root! Sorry =(
            parent_cid=command.notification.parent_ref.cid,  # This is a mis-nomer, should be root! Sorry =(
            latest_uri=latest_uri,
            latest_cid=latest_cid,
            complete=complete,
            authorized=authorized,
        )
    teardown_connection(get_database())


def update_bot_action(command, stage, latest_uri, latest_cid):
    """Updates the stage of an existing bot action."""
    action = command.notification.action
    action.stage = stage
    action.complete = stage == "complete"
    action.latest_uri = latest_uri
    action.latest_cid = latest_cid

    #db.connect(reuse_if_open=True)
    setup_connection(get_database())
    # Todo: not sure if atomic is needed here
    with get_database().atomic():
        action.save()
    teardown_connection(get_database())


def new_mod_action(
    did_mod: str, did_user: str, action: str, expiry: None | datetime = None
):
    """Register a new bot action in the database."""
    #db.connect(reuse_if_open=True)
    setup_connection(get_database())
    with get_database().atomic():
        ModActions.create(
            did_mod=did_mod, did_user=did_user, action=action, expiry=expiry
        )
    teardown_connection(get_database())


def new_signup(did, handle, valid=True):
    """Register a new account in the database."""
    #db.connect(reuse_if_open=True)
    setup_connection(get_database())
    # Last check to see if this account is already signed up - we won't add them again!
    account_entries = fetch_account_entry_for_did(did)
    already_signed_up = any([account.is_valid for account in account_entries])
    if already_signed_up:
        warnings.warn(
            f"Account {handle} is already signed up to the feeds! Unable to sign them up."
        )
        teardown_connection(get_database())
        return

    # Sign up a previously not validated account
    if not already_signed_up and len(account_entries) > 0:
        entry = account_entries[0]
        entry.is_valid = valid
        entry.feed_all = valid
        with get_database().atomic():
            entry.save()
            teardown_connection(get_database())
        return

    # OR, create a new signup!
    with get_database().atomic():
        Account.create(handle=handle, did=did, is_valid=valid, feed_all=valid)
    teardown_connection(get_database())


def get_outstanding_bot_actions(uris: None | list[str]) -> list:
    """Gets a list of all outstanding bot actions."""
    setup_connection(get_database())
    result: list
    if uris is None:
        result = [x for x in BotActions.select().where(
            BotActions.complete == False).execute()]  # noqa: E712
    else:
        result = [x for x in BotActions.select().where(
            BotActions.complete == False, BotActions.latest_uri << uris).execute()]
    # teardown_connection(get_database())
    return result


def get_candidate_stale_bot_actions(types: list, limit: int = 25, age: int = 28) -> peewee.ModelSelect:
    """Fetches all candidate stale bot actions, i.e. those that haven't had anything
    happen in a while.
    """
    setup_connection(get_database())

    results: peewee.ModelSelect = BotActions.select().where(BotActions.type << types,
            BotActions.complete == False,  # noqa: E712
            BotActions.indexed_at > datetime.now() - timedelta(days=age),
        ).order_by(BotActions.checked_at).limit(limit)

    # teardown_connection(get_database())
    return results


def update_checked_at_time_of_bot_actions(ids: list):
    setup_connection(get_database())
    with get_database().atomic():
        BotActions.update(checked_at=datetime.now(timezone.utc)).where(
            BotActions.id << ids
        ).execute()
    teardown_connection(get_database())
