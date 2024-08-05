"""A collection of all database actions for things the bot needs to do."""

import datetime
import warnings
from astrofeed_lib.database import BotActions, ModActions, db, Account


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
    db.connect(reuse_if_open=True)
    return [x for x in Account.select().where(Account.did == did)]



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


    db.connect(reuse_if_open=True)
    with db.atomic():
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


def update_bot_action(command, stage, latest_uri, latest_cid):
    """Updates the stage of an existing bot action."""
    action = command.notification.action
    action.stage = stage
    action.complete = stage == "complete"
    action.latest_uri = latest_uri
    action.latest_cid = latest_cid

    db.connect(reuse_if_open=True)
    # Todo: not sure if atomic is needed here
    with db.atomic():
        action.save()


def new_mod_action(
    did_mod: str, did_user: str, action: str, expiry: None | datetime.datetime = None
):
    """Register a new bot action in the database."""
    db.connect(reuse_if_open=True)
    with db.atomic():
        ModActions.create(
            did_mod=did_mod, did_user=did_user, action=action, expiry=expiry
        )


def new_signup(did, handle, valid=True):
    """Register a new account in the database."""
    db.connect(reuse_if_open=True)
    # Last check to see if this account is already signed up - we won't add them again!
    account_entries = fetch_account_entry_for_did(did)
    already_signed_up = any(
        [account.is_valid for account in account_entries]
    )
    if already_signed_up:
        warnings.warn(f"Account {handle} is already signed up to the feeds! Unable to sign them up.")
        return
    
    # Sign up a previously not validated account
    if not already_signed_up and len(account_entries) > 0:
        entry = account_entries[0]
        entry.is_valid = valid
        entry.feed_all = valid
        with db.atomic():
            entry.save()
        return

    # OR, create a new signup!
    with db.atomic():
        Account.create(handle=handle, did=did, is_valid=valid, feed_all=valid)


def get_outstanding_bot_actions(uris: None | list[str]) -> list:
    """Gets a list of all outstanding bot actions."""
    if uris is None:
        return [
            x
            for x in BotActions.select().where(BotActions.complete == False).execute()  # noqa: E712
        ]
    return [
        x
        for x in BotActions.select()
        .where(BotActions.complete == False, BotActions.latest_uri << uris)  # noqa: E712
        .execute()
    ]
