"""Commit processing components that work through posts and decide if they need to be
added to the feeds.
"""

import time
import traceback
from multiprocessing.sharedctypes import Synchronized
from astrofeed_lib.config import SERVICE_DID
from astrofeed_firehose.config import (
    EMPTY_QUEUE_SLEEP_TIME,
    COMMITS_TO_FETCH_AT_ONCE,
    FIREHOSE_CURSOR_UPDATE,
    DATABASE_CURSOR_UPDATE,
)
from astrofeed_firehose.apply_commit import apply_commit
from astrofeed_lib.database import (
    SubscriptionState,
    get_database,
    setup_connection,
    teardown_connection,
)
from faster_fifo import Queue
from queue import Empty
from atproto import parse_subscribe_repos_message
from atproto import models
from atproto.exceptions import ModelError
from astrofeed_lib import logger


def run_commit_processor(
    queue: Queue,
    cursor: Synchronized,  # Return value of multiprocessing.Value
    process_time: Synchronized,  # Return value of multiprocessing.Value
    op_counter: Synchronized | None = None,
) -> None:
    """Main commit processing method. This method takes commits from a faster_fifo Queue
    object and sees if they need to be added to the feeds or not.
    """
    logger.info("... commit processing worker started")
    error_count = 0

    while True:
        messages = _get_messages_from_queue(queue)

        # Todo update downstream functions to handle many at once, instead of having this for loop
        for message in messages:
            error_count = _process_commit_with_exception_wrapper(
                message, cursor, error_count
            )
            _update_process_time(process_time)
            _increment_op_count(op_counter)


def _get_messages_from_queue(queue: Queue):
    """Continually waits on the queue and tries to get messages from it."""
    while True:
        try:
            messages = queue.get_many(
                timeout=300, max_messages_to_get=COMMITS_TO_FETCH_AT_ONCE
            )
            break
        except Empty:
            time.sleep(EMPTY_QUEUE_SLEEP_TIME)
            continue
    return messages


def _process_commit_with_exception_wrapper(
    message, cursor: Synchronized, error_count: int
) -> int:
    """Attempt to process a single commit. This is a total exception wrapper that tries
    to catch any other random issues that could occur (out of spec commits can cause
    problems, for instance.)
    """
    try:
        cursor_value = _process_commit(message)
    except Exception:
        logger.exception(
            traceback.format_exc()
            + "Commit processing worker encountered an exception while processing "
            "a commit! This commit will be skipped."
        )
        error_count += 1
        logger.info(f"Error count: {error_count}")
    else:
        _update_cursor(cursor, cursor_value)

    return error_count


def _process_commit(message) -> int | None:
    """Attempt to process a single commit. Returns cursor value if successful."""
    # Skip any commits that do not pass this model (which can occur sometimes)
    try:
        commit = parse_subscribe_repos_message(message)
    except ModelError:
        logger.info("Unable to process a commit due to validation issue")
        return None

    # Final check that this is in fact a commit, and not e.g. a handle change
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return None

    # Apply commit to our database, looking for posts to add etc
    apply_commit(commit)

    # We return the current cursor value to the commit processor
    return commit.seq


def _update_cursor(cursor: Synchronized, value: int | None):
    """Updates the cursor in both the database & for what the firehose client holds."""
    if value is None:
        return

    # Update stored state every FIREHOSE_CURSOR_UPDATE events
    if value % FIREHOSE_CURSOR_UPDATE != 0:
        return
    cursor.value = value

    # We also update the stored database state every DATABASE_CURSOR_UPDATE events
    if value % DATABASE_CURSOR_UPDATE != 0:
        return
    setup_connection(get_database())
    SubscriptionState.update(cursor=value).where(
        SubscriptionState.service == SERVICE_DID
    ).execute()
    teardown_connection(get_database())


def _update_process_time(time_object: Synchronized):
    """Updates the last-active time of the commit processing process (used to detect)
    whether or not it has hung.
    """
    time_object.value = time.time()


def _increment_op_count(op_counter: Synchronized | None):
    """Increments the total number of operations (commits) handled by the firehose
    processor since startup.
    """
    if op_counter is not None:
        op_counter.value += 1
