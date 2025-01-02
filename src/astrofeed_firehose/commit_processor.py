"""Commit processing components that work through posts and decide if they need to be
added to the feeds.
"""

import logging
import multiprocessing
import time
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import Connection, wait
from astrofeed_firehose.process_updates import (
    ExistingPostsUpdate,
    NewPostUpdate,
    ProcessUpdate,
    ValidAccountsUpdate,
)
from astrofeed_firehose.commit import _process_commit
from astrofeed_lib.accounts import AccountQuery
from astrofeed_lib.posts import PostQuery


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_commit_processor(
    receiver: Connection,
    cursor: Synchronized,
    worker_time: Synchronized,
    n_workers: int = 2,
    update_cursor_in_database: bool = True,
    measurement_interval: int | float = 60,
    account_update_interval: int | float = 60,
    post_update_interval: int | float = 86400,
) -> None:
    """Runs multiple commit processing processes at once. Effectively a reimplementation
    of multiprocessing.Queue logic, except compatible with AWS and with some additional
    synchronisation logic to try and avoid post deletion race conditions.

    See https://stackoverflow.com/q/34005930 for more information on why
    multiprocessing.Queue isn't used here.
    """
    # Todo: Most functions here have way too many arguments and could be refactored.
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

    logger.info("All resources initialised. Beginning message sending process.")

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


def _run_commit_processor_worker(
    pipe: Connection,
    cursor: Synchronized,
    update_cursor_in_database: bool = True,
) -> None:
    """Main sub-worker handler!

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
                logger.info("... received posts update")
            elif isinstance(message, ValidAccountsUpdate):
                valid_accounts = message.accounts
                logger.info("... received accounts update")
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
    logger.info("Fetching initial data")
    next_account_update_time = time.time() + account_update_interval
    next_post_update_time = time.time() + post_update_interval
    account_query = AccountQuery()
    post_query = PostQuery()
    accounts_update = ValidAccountsUpdate(account_query.get_accounts())
    posts_update = ExistingPostsUpdate(post_query.get_posts())

    # Initialise every process
    for i in range(n_workers):
        logger.info(f"Initialising worker {i}")
        # Make required multiprocessing resources
        parent, child = multiprocessing.Pipe()
        parent_connections.append(parent)
        processes.append(
            multiprocessing.Process(
                target=_run_commit_processor_worker,
                args=(child, cursor),
                kwargs=dict(update_cursor_in_database=update_cursor_in_database),
                name=f"Commit processing worker {i}",
            )
        )

        logger.info(f"Starting worker {i}")
        processes[-1].start()

        # Fill pipe with initial info
        logger.info(f"Sending data to worker {i}")
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


def _assign_message_to_process(available_connections, running_connections, message):
    """Assigns a new message to an available connection."""
    if len(available_connections) < 1:
        raise RuntimeError("No connections are available to assign a message to.")
    conn = available_connections.pop(0)
    conn.send(message)
    running_connections.append(conn)


def _update_parent_watchdog(worker_time):
    """Tell the parent watchdog process that we're still running"""
    # Todo add additional watchdog stuff for this process' sub-processes
    current_time = time.time()
    worker_time.value = current_time
    return current_time


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
