"""Moderation-related actions."""

from astrofeed_lib.accounts import CachedModeratorList
from astrobot.database import new_mod_action, new_signup, hide_post_by_uri, ban_user_by_did
from astrofeed_lib import logger


# Setup list of moderators
MODERATORS = CachedModeratorList(query_interval=60)


def ban_user(did: str, did_mod: str, reason: str):
    """Bans a user from the Astronomy feeds."""
    success, explanation = ban_user_by_did(did)

    if success:
        logger.info(
            f"Banning account with DID {did} from the feeds. Mod: {did_mod}. Reason: {reason}."
        )
        new_mod_action(did_mod, did, "ban")
    else:
        logger.info(f"Failed to ban accound with DID {did}. Mod: {did_mod}")

    return explanation


def mute_user(did: str, did_mod: str, reason: str, days: int):
    """Mutes a user from the Astronomy feeds."""
    logger.info(
        f"Muting account with DID {did} from the feeds. Mod: {did_mod}. Reason: {reason}. Duration: {days} days."
    )
    # todo
    raise NotImplementedError("mute_user not implemented")


def signup_user(did: str, did_mod: str, handle: str = "undefined", valid: bool = True):
    """Signs a user up to the Astronomy feeds."""
    logger.info(f"Signing up {handle} to the feeds. Mod: {did_mod}")
    new_mod_action(did_mod, did, "signup")
    new_signup(did, handle, valid=valid)


def cancel_signup(did: str, did_mod: str):
    logger.info(f"Cancelling signup for user {did}. Mod: {did_mod}")
    new_mod_action(did_mod, did, "signup_cancelled")


def hide_post(uri: str, did: str, did_mod: str):
    success, explanation = hide_post_by_uri(uri, did)

    if success:
        logger.info(f"Hiding post by user {did}. Mod: {did_mod}")
        new_mod_action(did_mod, did, "hide")
    else:
        logger.info(f"Failed to hide post by user {did}. Mod: {did_mod}")

    return explanation
