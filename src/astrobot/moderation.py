"""Moderation-related actions."""

from astrofeed_lib.database import Account


def get_moderators(minimum_level: int = 1) -> set[str]:
    """Returns a set containing the DIDs of all current moderators."""
    query = Account.select(Account.did).where(Account.mod_level >= minimum_level)
    return {user.did for user in query.execute()}


def ban_user(reason: str):
    """Bans a user from the Astronomy feeds."""
    # todo
    raise NotImplementedError("ban_user not implemented")


def mute_user(reason: str, days: int):
    """Mutes a user from the Astronomy feeds."""
    # todo
    raise NotImplementedError("mute_user not implemented")
