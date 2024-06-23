"""Moderation-related actions."""

from astrofeed_lib.accounts import CachedAccountQuery
from astrofeed_lib.database import Account


class CachedModeratorList(CachedAccountQuery):
    def __init__(self, minimum_level: int = 1, query_interval=60 * 10, **kwargs):
        super().__init__(query_interval=query_interval, **kwargs)
        self.minimum_level = minimum_level

    def account_query(self):
        return get_moderators(self.minimum_level)


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
