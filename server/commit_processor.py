"""Commit processing components that work through posts and decide if they need to be
added to the feeds.
"""
import logging
import multiprocessing
import time
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import Connection, wait
from atproto import parse_subscribe_repos_message
from atproto import models
from atproto.exceptions import ModelError
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState, db
from server.commit import apply_commit
from astrofeed_lib.accounts import AccountQuery
from astrofeed_lib.posts import PostQuery


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ProcessUpdate:
    """Base class for any update to be sent between processes."""

    pass


class NewPostUpdate(ProcessUpdate):
    """Notify that a new post has been added and needs to be communicated to all
    other subprocesses so that post liking and deletion can keep working.
    """

    def __init__(self, uri):
        self.uri = uri


class ExistingPostsUpdate(ProcessUpdate):
    """Sent from manager to subprocess, this updates the subprocess on the current list
    of posts that it should check when processing likes and deletions.
    """

    def __init__(self, posts):
        self.posts = posts


class ValidAccountsUpdate(ProcessUpdate):
    """Sent from manager to subprocess, this updates the subprocess on the current list
    of accounts that are authorized to post to the Astronomy feeds and should be
    tracked.
    """

    def __init__(self, accounts):
        self.accounts = accounts


def _process_commit(
    message, cursor, valid_accounts, existing_posts, update_cursor_in_database=True
):
    """Attempt to process a single commit. Returns a list of any new posts to add."""
    # Skip any commits that do not pass this model (which can occur sometimes)
    try:
        commit = parse_subscribe_repos_message(message)
    except ModelError:
        logger.exception("Unable to process a commit due to validation issue")
        return []

    # Final check that this is in fact a commit, and not e.g. a handle change
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return []

    new_posts = apply_commit(commit, valid_accounts, existing_posts)

    # Update stored state every ~100 events
    if commit.seq % 100 == 0:
        cursor.value = commit.seq
        if commit.seq % 1000 == 0:
            if update_cursor_in_database:
                db.connect(reuse_if_open=True)
                SubscriptionState.update(cursor=commit.seq).where(
                    SubscriptionState.service == SERVICE_DID
                ).execute()
                db.close()
            else:
                logger.info(f"Cursor: {commit.seq}")

    # Notify the manager process of either a) a new post, or b) that we're done with
    # this commit
    return new_posts


def _run_commit_processor(
    pipe: Connection,
    cursor: Synchronized,
    update_cursor_in_database: bool = True,
) -> None:
    """Main worker handler!

    Currently, on an exception when handling a post, the worker will restart (skipping
    that post). This should be very rare.
    """
    logger.info("... commit processing worker started")
    error_count = 0
    valid_accounts = set()
    existing_posts = set()

    while True:
        # Wait for the multiprocessing.connection.Connection to contain something.
        # This is blocking, btw!
        message = pipe.recv()

        if isinstance(message, ProcessUpdate):
            if isinstance(message, NewPostUpdate):
                existing_posts.add(message.uri)
            elif isinstance(message, ExistingPostsUpdate):
                existing_posts = message.posts
            elif isinstance(message, ValidAccountsUpdate):
                valid_accounts = message.accounts
            else:
                raise RuntimeError(
                    "Unidentified update received through pipe with type "
                    f"{type(message)}: {message}"
                )
            continue

        try:
            result = _process_commit(
                message,
                cursor,
                valid_accounts,
                existing_posts,
                update_cursor_in_database=update_cursor_in_database,
            )
        except Exception:
            logger.exception(
                "Post processing worker encountered an exception while processing a "
                "post! This post will be skipped."
            )
            result = []
            error_count += 1
            logger.info(f"Error count: {error_count}")

        if result:
            for post in result:
                pipe.send(NewPostUpdate(post))
        else:
            pipe.send(0)


def _get_finished_processes(running_connections, available_connections):
    """Returns the pipes of any processes that are finished with their tasks."""
    # If all processes are busy, wait for one to finish
    if not available_connections:
        return wait(running_connections)

    # OR, return any that have results
    return wait(running_connections, timeout=0)


def _synchronize_between_processes(finished_connections, parent_connections):
    """Synchronizes state across processes if any have anything important (like a new
    post to report.)"""
    for a_finished_connection in finished_connections:
        action = a_finished_connection.recv()  # type: ignore

        if isinstance(action, NewPostUpdate):
            for conn in parent_connections:
                conn.send(action)


def _update_available_processes(
    available_connections, finished_connections, running_connections
):
    """Updates the list of available processes and returns a list of which are still
    running.
    """
    available_connections.extend(finished_connections)
    return [conn for conn in running_connections if conn not in finished_connections]


def _refresh_process_information(
    account_update_interval,
    post_update_interval,
    parent_connections,
    next_account_update_time,
    next_post_update_time,
    account_query,
    post_query,
    current_time,
):
    """Optionally refreshes information that all subprocesses currently hold, if
    necessary.

    # Todo this function has an absurd number of arguments. Can it be refactored to be neater?
    """
    if current_time > next_account_update_time:
        next_account_update_time = _refresh_process_account_lists(
            account_update_interval, parent_connections, account_query, current_time
        )
    if current_time > next_post_update_time:
        next_post_update_time = _refresh_process_post_lists(
            post_update_interval, parent_connections, post_query, current_time
        )
    return next_account_update_time, next_post_update_time


def _refresh_process_post_lists(
    post_update_interval, parent_connections, post_query, current_time
):
    logger.info("Refreshing list of posts.")
    posts_update = ExistingPostsUpdate(post_query.get_posts())
    for conn in parent_connections:
        conn.send(posts_update)
    return current_time + post_update_interval


def _refresh_process_account_lists(
    account_update_interval, parent_connections, account_query, current_time
):
    logger.info("Refreshing list of active accounts.")
    accounts_update = ValidAccountsUpdate(account_query.get_accounts())
    for conn in parent_connections:
        conn.send(accounts_update)
    return current_time + account_update_interval


def _write_ops_per_second_to_log(
    measurement_interval, measurement_time, total_ops, current_time
):
    """Logs how many ops are running per second to the logger."""
    total_ops += 1
    if current_time > measurement_time:
        logger.info(f"Running at {total_ops / measurement_interval:.2f} ops/second")
        total_ops = 0
        measurement_time += measurement_interval
    return total_ops, measurement_time


def _update_process_state(
    parent_connections, available_connections, running_connections
):
    """Perform updates and state to do with running processes that could have changed
    since we last checked.
    """
    finished_connections = _get_finished_processes(
        running_connections, available_connections
    )
    _synchronize_between_processes(finished_connections, parent_connections)
    return _update_available_processes(
        available_connections, finished_connections, running_connections
    )


def _update_parent_watchdog(worker_time):
    """Tell the parent watchdog process that we're still running"""
    # Todo add additional watchdog stuff for this process' sub-processes
    current_time = time.time()
    worker_time.value = current_time
    return current_time


def _assign_message_to_process(available_connections, running_connections, message):
    """Assigns a new message to an available connection."""
    if len(available_connections) < 1:
        raise RuntimeError("No connections are available to assign a message to.")
    conn = available_connections.pop(0)
    conn.send(message)
    running_connections.append(conn)


def run_commit_processor_multithreaded(
    receiver: Connection,
    cursor: Synchronized,
    worker_time: Synchronized,
    n_workers: int = 2,
    update_cursor_in_database: bool = True,
    measurement_interval: int | float = 60,
    account_update_interval: int | float = 600,
    post_update_interval: int | float = 86400,
) -> None:
    """Runs multiple commit processing processes at once. Effectively a reimplementation
    of multiprocessing.Queue logic, except compatible with AWS and with some additional
    synchronisation logic to try and avoid post deletion race conditions.

    See https://stackoverflow.com/q/34005930 for more information on why
    multiprocessing.Queue isn't used here.
    """
    logger.info("Booting up commit processing manager.")
    (
        parent_connections,
        available_connections,
        account_query,
        post_query,
        next_account_update_time,
        next_post_update_time,
        running_connections,
    ) = _initialise_resources(
        cursor,
        n_workers,
        update_cursor_in_database,
        account_update_interval,
        post_update_interval,
    )

    measurement_time = time.time() + measurement_interval
    total_ops = 0

    while True:
        # Wait for new firehose event (blocking)
        message = receiver.recv()

        running_connections = _update_process_state(
            parent_connections, available_connections, running_connections
        )
        _assign_message_to_process(available_connections, running_connections, message)
        current_time = _update_parent_watchdog(worker_time)
        total_ops, measurement_time = _write_ops_per_second_to_log(
            measurement_interval, measurement_time, total_ops, current_time
        )
        next_account_update_time, next_post_update_time = _refresh_process_information(
            account_update_interval,
            post_update_interval,
            parent_connections,
            next_account_update_time,
            next_post_update_time,
            account_query,
            post_query,
            current_time,
        )


def _initialise_resources(
    cursor,
    n_workers,
    update_cursor_in_database,
    account_update_interval,
    post_update_interval,
):
    """Initialises resources for the commit processing manager."""
    # Make lists to store stuff in
    parent_connections, processes = [], []
    available_connections, running_connections = [], []

    # Get initial post & account query lists
    next_account_update_time = time.time() + account_update_interval
    next_post_update_time = time.time() + post_update_interval
    account_query = AccountQuery(with_database_closing=True)
    post_query = PostQuery(with_database_closing=True)
    accounts_update = ValidAccountsUpdate(account_query.get_accounts())
    posts_update = ExistingPostsUpdate(post_query.get_posts())

    # Initialise every process
    for i in range(n_workers):
        # Make required multiprocessing resources
        parent, child = multiprocessing.Pipe()
        parent_connections.append(parent)
        processes.append(
            multiprocessing.Process(
                target=_run_commit_processor,
                args=(child, cursor),
                kwargs=dict(update_cursor_in_database=update_cursor_in_database),
                name=f"Commit processing worker {i}",
            )
        )
        processes[-1].start()

        # Fill pipe with initial info
        parent.send(accounts_update)
        parent.send(posts_update)
        
    available_connections = parent_connections

    logger.info(f"Started {len(processes)} commit processing workers.")

    # Todo can this be returned in a less horrific way please? :D suggestion: have a class holding connections + processes and a class holding query information
    return (
        parent_connections,
        available_connections,
        account_query,
        post_query,
        next_account_update_time,
        next_post_update_time,
        running_connections,
    )
