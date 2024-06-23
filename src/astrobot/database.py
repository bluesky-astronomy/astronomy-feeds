"""A collection of all database actions for things the bot needs to do."""

import datetime
from astrofeed_lib.database import BotActions, ModActions, db


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


def new_bot_action(command, stage="complete", complete=True):
    """Save a new bot action to the database."""
    db.connect(reuse_if_open=True)
    with db.atomic():
        BotActions.create(
            did=command.notification.author.did,
            type=command.command,
            stage=stage,
            parent_uri=command.notification.parent_ref.uri,
            parent_cid=command.notification.parent_ref.cid,
            latest_uri=command.notification.parent_ref.uri,
            latest_cid=command.notification.parent_ref.cid,
            complete=complete,
        )


def new_mod_action(
    did_mod: str, did_user: str, action: str, expiry: None | datetime.datetime = None
):
    db.connect(reuse_if_open=True)
    with db.atomic():
        ModActions.create(
            did_mod=did_mod, did_user=did_user, action=action, expiry=expiry
        )


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
