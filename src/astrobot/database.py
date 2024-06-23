"""A collection of all database actions for things the bot needs to do."""

import datetime
from astrofeed_lib.database import BotActions, ModActions
from atproto_client.models.app.bsky.notification.list_notifications import Notification


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


def new_bot_action(**kwargs):
    # Todo: change to something like model-based validation
    if any([k not in kwargs for k in REQUIRED_BOT_ACTION_FIELDS]):
        raise ValueError("kwargs is missing required fields. Kwargs:", kwargs)
    BotActions.create(**kwargs)


def new_mod_action(
    did_mod: str, did_user: str, action: str, expiry: None | datetime.datetime = None
):
    ModActions.create(did_mod=did_mod, did_user=did_user, action=action, expiry=expiry)


def get_outstanding_bot_actions(uris: None | list[str]) -> list:
    """Gets a list of all outstanding bot actions."""
    if uris is None:
        return [
            x
            for x in BotActions.select().where(BotActions.complete == False).execute()  # noqa: E712
        ]
    return [x for x in 
        BotActions.select()
        .where(BotActions.complete == False, BotActions.latest_uri << uris)  # noqa: E712
        .execute()
    ]
