"""Code for client that connects to firehose."""

import logging
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import Connection
import time
from atproto.exceptions import FirehoseError
from atproto import AsyncFirehoseSubscribeReposClient
from atproto import firehose_models
from atproto import models, CAR, AtUri, parse_subscribe_repos_message
from atproto_client.models.common import XrpcError
from atproto.exceptions import ModelError
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState
from .commit import _get_ops_by_type
import uvloop


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_client(
    cursor: Synchronized,  # Return value of multiprocessing.Value
    pipe: Connection,
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
    start_cursor: int | None = None,
    base_uri: str = "wss://bsky.network/xrpc",
):
    uvloop.run(
        run_client_async(
            cursor, pipe, firehose_time, start_cursor=start_cursor, base_uri=base_uri
        )
    )


measurement_time = time.time()
total_ops = 0


async def run_client_async(
    cursor: Synchronized,  # Return value of multiprocessing.Value
    pipe: Connection,
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
    start_cursor: int | None = None,
    base_uri: str = "wss://bsky.network/xrpc",
):
    """Primary function for running the client that connects to Bluesky. New commits are
    immediately sent to the separate post processing worker.
    """

    async def on_message_handler(message: firehose_models.MessageFrame) -> None:
        """This handler tells the client what to do when a new commit is encountered."""
        ops = parse_message(message)

        if ops:
            if ops['has_ops']:
                # Send it to post processing worker to handle
                pipe.send(ops)

        # Update local client cursor value
        if cursor.value:
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=cursor.value)
            )
            cursor.value = 0

        # Update current working time so that the watchdog knows this process is running
        now = time.time()
        firehose_time.value = now

        # Update user on ops/second
        global total_ops, measurement_time
        total_ops += 1

        if (interval := now - measurement_time) > 60:
            logger.info(f"Running at {total_ops / interval:.2f} ops/second")
            total_ops = 0
            measurement_time = now



    # Continually restarts the client if ConsumerTooSlow errors are encountered. This
    # can happen due to the Bluesky network being busy or internet connection issues.
    while True:
        client = _get_client(start_cursor=start_cursor, base_uri=base_uri)

        try:
            logger.info("... firehose client worker started")
            await client.start(on_message_handler)

        except FirehoseError as e:
            if not _is_client_too_slow_error(e):
                raise e
            logger.warn("Reconnecting to Firehose due to ConsumerTooSlow...")


def parse_message(message):
    # Skip any commits that do not pass this model (which can occur sometimes)
    try:
        commit = parse_subscribe_repos_message(message)
    except ModelError:
        logger.exception("Unable to process a commit due to validation issue")
        return []

    # Final check that this is in fact a commit, and not e.g. a handle change
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return []
    
    ops = _get_ops_by_type(commit)

    return ops


def _get_client(
    start_cursor: int | None = None, base_uri: str = "wss://bsky.network/xrpc"
):
    if start_cursor is None:
        start_cursor = _get_start_cursor()
    params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=start_cursor)
    return AsyncFirehoseSubscribeReposClient(params, base_uri=base_uri)


def _get_start_cursor():
    # Get current saved cursor value
    start_cursor = SubscriptionState.get(
        SubscriptionState.service == SERVICE_DID
    ).cursor
    if start_cursor:
        if not isinstance(start_cursor, int):
            raise ValueError(f"Saved cursor with value '{start_cursor}' is invalid.")
        return start_cursor

    # If there isn't one, then make sure the DB has a cursor
    logger.info("Generating a cursor for the first time...")
    SubscriptionState.create(service=SERVICE_DID, cursor=0)
    return None


def _is_client_too_slow_error(e):
    xrpc_error = e.args[0]
    return isinstance(xrpc_error, XrpcError) and xrpc_error.error == "ConsumerTooSlow"
