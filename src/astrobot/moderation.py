"""Moderation-related actions."""

from astrofeed_lib.accounts import CachedModeratorList
from astrobot.database import new_mod_action, new_signup


# Setup list of moderators
MODERATORS = CachedModeratorList(query_interval=60)


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
