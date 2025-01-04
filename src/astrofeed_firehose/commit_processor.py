"""Commit processing components that work through posts and decide if they need to be
added to the feeds.
"""

import logging
import time
from multiprocessing.sharedctypes import Synchronized
from astrofeed_lib.config import SERVICE_DID
from astrofeed_firehose.apply_commit import apply_commit
from astrofeed_lib.database import (
    SubscriptionState,
    get_database,
    setup_connection,
    teardown_connection,
)
from faster_fifo import Queue
from queue import Empty, Full
from atproto import CAR, AtUri, parse_subscribe_repos_message
from atproto import models
from atproto.exceptions import ModelError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_commit_processor(
    queue: Queue,
    cursor: Synchronized,  # Return value of multiprocessing.Value
    process_time: Synchronized,  # Return value of multiprocessing.Value
) -> None:
    """Main sub-worker handler!

    Currently, on an exception when handling a post, the worker will restart (skipping
    that post). This should be very rare.
    """
    logger.info("... commit processing worker started")
    error_count = 0

    while True:
        # Wait for the queue to contain something.
        # Todo: upgrade to get_many eventually, reducing lock overhead
        message = queue.get(timeout=300)

        try:
            cursor_value = _process_commit(message)
        except Exception:
            logger.exception(
                "Post processing worker encountered an exception while processing a "
                "post! This post will be skipped."
            )
            error_count += 1
            logger.info(f"Error count: {error_count}")
        else:
            _update_cursor(cursor_value, cursor)
        
        _update_process_time(process_time)


def _process_commit(message):
    """Attempt to process a single commit. Returns a list of any new posts to add."""
    # Skip any commits that do not pass this model (which can occur sometimes)
    try:
        commit = parse_subscribe_repos_message(message)
    except ModelError:
        print("Unable to process a commit due to validation issue")
        return None

    # Final check that this is in fact a commit, and not e.g. a handle change
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return None

    # Apply commit to our database, looking for posts to add etc
    apply_commit(commit)

    # We return the current cursor value to the commit processor
    return commit.seq


def _update_cursor(value: int | None, cursor: Synchronized):
    if value is None:
        return

    # Update stored state every ~100 events
    # Todo: see if this can be increased to 1000
    if value % 100 != 0:
        return
    cursor.value = value

    # We also update the stored database state
    # Todo: see if this can be increased to 10000, which is <1 minute of ops/sec
    if value % 1000 != 0:
        return
    setup_connection(get_database())
    SubscriptionState.update(cursor=value).where(
        SubscriptionState.service == SERVICE_DID
    ).execute()
    teardown_connection(get_database())


def _update_process_time(time_object: Synchronized):
    time_object.value = time.time()
