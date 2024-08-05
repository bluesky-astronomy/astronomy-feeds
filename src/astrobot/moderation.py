"""Moderation-related actions."""

from astrofeed_lib.accounts import CachedAccountQuery
from astrofeed_lib.database import Account
from astrobot.database import new_mod_action, new_signup


class CachedModeratorList(CachedAccountQuery):
    def account_query(self):
        return get_moderators()
    
    def get_accounts_above_level(self, minimum_level: int) -> set[str]:
        """Wraps get_accounts and returns only moderators with the desired minimum
        level.
        """
        return {did for did, level in self.get_accounts() if level >= minimum_level}


# Setup list of moderators
MODERATORS = CachedModeratorList()


def get_moderators() -> dict[str, int]:
    """Returns a set containing the DIDs of all current moderators."""
    query = Account.select(Account.did).where(Account.mod_level >= 1)
    return {user.did: user.mod_level for user in query.execute()}


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
