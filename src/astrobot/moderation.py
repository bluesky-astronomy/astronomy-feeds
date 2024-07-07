"""Moderation-related actions."""

from astrofeed_lib.accounts import CachedAccountQuery
from astrofeed_lib.database import Account
from astrobot.database import new_mod_action, new_signup


class CachedModeratorList(CachedAccountQuery):
    def __init__(self, minimum_level: int = 1, query_interval=60 * 10, **kwargs):
        super().__init__(query_interval=query_interval, **kwargs)
        self.minimum_level = minimum_level

    def account_query(self):
        return get_moderators(self.minimum_level)


# Setup list of moderators
MODERATORS = CachedModeratorList(minimum_level=1)


def get_moderators(minimum_level: int = 1) -> set[str]:
    """Returns a set containing the DIDs of all current moderators."""
    query = Account.select(Account.did).where(Account.mod_level >= minimum_level)
    return {user.did for user in query.execute()}


def ban_user(did: str, did_mod: str, reason: str):
    """Bans a user from the Astronomy feeds."""
    print(
        f"Banning account with DID {did} from the feeds. Mod: {did_mod}. Reason: {reason}."
    )
    # todo
    raise NotImplementedError("ban_user not implemented")


def mute_user(did: str, did_mod: str, reason: str, days: int):
    """Mutes a user from the Astronomy feeds."""
    print(
        f"Muting account with DID {did} from the feeds. Mod: {did_mod}. Reason: {reason}. Duration: {days} days."
    )
    # todo
    raise NotImplementedError("mute_user not implemented")


def signup_user(did: str, did_mod: str, handle: str = "undefined",  valid: bool = True):
    """Signs a user up to the Astronomy feeds."""
    print(f"Signing up {handle} to the feeds. Mod: {did_mod}")
    new_mod_action(did_mod, did, "signup")
    new_signup(did, handle, valid=valid)
