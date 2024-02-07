"""Commit processing components that work through posts and decide if they need to be
added to the feeds.
"""
import logging
import multiprocessing
import time
import os
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import Connection, wait
from atproto import CAR, AtUri
from atproto import parse_subscribe_repos_message
from atproto import models
from atproto.exceptions import ModelError
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState, db
from server.data_filter import operations_callback
from astrofeed_lib.accounts import AccountQuery
from astrofeed_lib.posts import PostQuery


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ProcessUpdate:
    pass


class NewPostUpdate(ProcessUpdate):
    def __init__(self, uri):
        self.uri = uri


class ExistingPostsUpdate(ProcessUpdate):
    def __init__(self, posts):
        self.posts = posts


class ValidAccountsUpdate(ProcessUpdate):
    def __init__(self, accounts):
        self.accounts = accounts


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> dict:  # noqa: C901
    """Sorts all commits/operations by type into a convenient to process dictionary."""
    operation_by_type = {
        "posts": {"created": [], "deleted": []},
        "reposts": {"created": [], "deleted": []},
        "likes": {"created": [], "deleted": []},
        "follows": {"created": [], "deleted": []},
    }

    # Handle occasional empty commit (not in ATProto spec but seems to happen sometimes.
    # Can be a blank binary string sometimes, for no reason)
    if not commit.blocks:
        return operation_by_type

    car = CAR.from_bytes(commit.blocks)  # type: ignore

    for op in commit.ops:
        uri = AtUri.from_str(f"at://{commit.repo}/{op.path}")

        if op.action == "update":
            # not supported yet
            continue

        if op.action == "create" and car is not None:
            if not op.cid:
                continue

            create_info = {"uri": str(uri), "cid": str(op.cid), "author": commit.repo}

            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            record = models.get_or_create(record_raw_data, strict=False)
            if uri.collection == models.ids.AppBskyFeedPost and models.is_record_type(
                record,  # type: ignore
                models.ids.AppBskyFeedPost,
            ):
                operation_by_type["posts"]["created"].append(
                    {"record": record, **create_info}
                )

            # The following types of event don't need to be tracked by the feed right now, and are removed.
            # elif uri.collection == ids.AppBskyFeedLike and is_record_type(record, ids.AppBskyFeedLike):
            #     operation_by_type['likes']['created'].append({'record': record, **create_info})
            # elif uri.collection == ids.AppBskyFeedRepost and is_record_type(record, ids.AppBskyFeedRepost):
            #     operation_by_type['reposts']['created'].append({'record': record, **create_info})
            # elif uri.collection == ids.AppBskyGraphFollow and is_record_type(record, ids.AppBskyGraphFollow):
            #     operation_by_type['follows']['created'].append({'record': record, **create_info})

        if op.action == "delete":
            if uri.collection == models.ids.AppBskyFeedPost:
                operation_by_type["posts"]["deleted"].append({"uri": str(uri)})

            # The following types of event don't need to be tracked by the feed right now.
            # elif uri.collection == ids.AppBskyFeedLike:
            #     operation_by_type['likes']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyFeedRepost:
            #     operation_by_type['reposts']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyGraphFollow:
            #     operation_by_type['follows']['deleted'].append({'uri': str(uri)})

    return operation_by_type


def _process_commit(
    message, cursor, valid_accounts, existing_posts, update_cursor_in_database=True
):
    # Skip any commits that do not pass this model (which can occur sometimes)
    try:
        commit = parse_subscribe_repos_message(message)
    except ModelError:
        logger.exception("Unable to process a commit due to validation issue")
        return []

    # Final check that this is in fact a commit, and not e.g. a handle change
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        # logger.error(
        #     "A commit is not a models.ComAtprotoSyncSubscribeRepos.Commit instance"
        # )
        # logger.info(commit)
        return []

    new_posts = operations_callback(
        _get_ops_by_type(commit), commit.seq, valid_accounts, existing_posts
    )

    # Update stored state every ~100 events
    if commit.seq % 100 == 0:
        cursor.value = commit.seq
        if update_cursor_in_database:
            db.connect(reuse_if_open=True)  # Todo: not sure if needed
            SubscriptionState.update(cursor=commit.seq).where(
                SubscriptionState.service == SERVICE_DID
            ).execute()
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


def run_commit_processor_multithreaded(
    receiver: Connection,
    cursor: Synchronized,
    worker_time: Synchronized,
    n_workers: int = 2,
    update_cursor_in_database: bool = True,
    measurement_interval: int | float = 5,
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
    # Sadly, everything here has to be done with lists thanks to how
    # multiprocessing.connection.wait works...
    parent_connections, processes = [], []
    available_connections, running_connections = [], []

    # Initialise starting data on posts & accounts
    next_account_update_time = time.time() + account_update_interval
    next_post_update_time = time.time() + post_update_interval
    account_query = AccountQuery(with_database_closing=True)
    post_query = PostQuery(with_database_closing=True)
    accounts_update = ValidAccountsUpdate(account_query.get_accounts())
    posts_update = ExistingPostsUpdate(post_query.get_posts())

    # Allocate resources
    for i in range(n_workers):
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

        # Send initial data to processes
        parent.send(accounts_update)
        parent.send(posts_update)

    for process in processes:
        process.start()
    available_connections = parent_connections

    logger.info(f"Started {len(processes)} commit processing workers.")

    measurement_time = time.time() + measurement_interval
    total_ops = 0

    while True:
        # Wait for new firehose event
        message = receiver.recv()

        # Wait for any processes to finish
        if not available_connections:
            finished_connections = wait(running_connections)
        # If we have an available connection, we can also check to see if any are done
        else:
            finished_connections = wait(running_connections, timeout=0)

        # Ensure we synchronise state nicely
        for a_finished_connection in finished_connections:
            action = a_finished_connection.recv()  # type: ignore

            if isinstance(action, NewPostUpdate):
                for conn in parent_connections:
                    conn.send(action)

        # Refresh available / unavailable connections
        available_connections.extend(finished_connections)
        running_connections = [
            conn for conn in running_connections if conn not in finished_connections
        ]

        # Assign message to new connection
        conn = available_connections.pop(0)
        conn.send(message)
        running_connections.append(conn)

        # Tell the watchdog that we're still running
        # Todo add additional watchdog stuff for this process' sub-processes
        current_time = time.time()
        worker_time.value = current_time

        # Keep record of n ops being ran
        total_ops += 1
        if current_time > measurement_time:
            logger.info(f"Running at {total_ops / measurement_interval:.2f} ops/second")
            total_ops = 0
            measurement_time += measurement_interval

        # Send any updates to connections
        if current_time > next_account_update_time:
            logger.info("Refreshing list of active accounts.")
            accounts_update = ValidAccountsUpdate(account_query.get_accounts())
            for conn in parent_connections:
                conn.send(accounts_update)
            next_account_update_time = current_time + account_update_interval
        if current_time > next_post_update_time:
            logger.info("Refreshing list of posts.")
            posts_update = ExistingPostsUpdate(post_query.get_posts())
            for conn in parent_connections:
                conn.send(posts_update)
            next_post_update_time = current_time + post_update_interval
