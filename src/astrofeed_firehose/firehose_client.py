"""Code for client that connects to firehose."""

import logging
from multiprocessing.sharedctypes import Synchronized
import time
from atproto.exceptions import FirehoseError
from atproto import AsyncFirehoseSubscribeReposClient
from atproto import firehose_models
from atproto import models
from atproto_client.models.common import XrpcError
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import (
    SubscriptionState,
    setup_connection,
    teardown_connection,
    get_database,
)
from astrofeed_firehose.config import BASE_URI, CURSOR_OVERRIDE
import uvloop
from faster_fifo import Queue
from queue import Full


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_client(
    queue: Queue,
    cursor: Synchronized,  # Return value of multiprocessing.Value
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
):
    # We run the client with uvloop as it's a little bit quicker than basic Python
    uvloop.run(
        run_client_async(
            queue, cursor, firehose_time
        )
    )


async def run_client_async(
    queue: Queue,
    cursor: Synchronized,  # Return value of multiprocessing.Value
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
):
    """Primary function for running the client that connects to Bluesky. New commits are
    immediately sent to the separate post processing worker.
    """

    async def on_message_handler(message: firehose_models.MessageFrame) -> None:
        """This handler tells the client what to do when a new commit is encountered."""
        while True:
            try:
                queue.put(message, timeout=0.1)
                break
            except Full:
                logger.warning("Queue is full")
                time.sleep(1)

        # Update local client cursor value
        if cursor.value:
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=cursor.value)
            )
            cursor.value = 0

        # Update current working time so that the watchdog knows this process is running
        firehose_time.value = time.time()

    # Continually restarts the client if ConsumerTooSlow errors are encountered. This
    # can happen due to the Bluesky network being busy or internet connection issues.
    while True:
        client = _get_client(start_cursor=CURSOR_OVERRIDE, base_uri=BASE_URI)

        try:
            logger.info("... firehose client worker started")
            await client.start(on_message_handler)

        except FirehoseError as e:
            if not _is_client_too_slow_error(e):
                raise e
            logger.warning("Reconnecting to Firehose due to ConsumerTooSlow...")


def _get_client(
    start_cursor: int | None = None, base_uri: str = "wss://bsky.network/xrpc"
):
    if start_cursor is None:
        start_cursor = _get_start_cursor()
    params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=start_cursor)
    return AsyncFirehoseSubscribeReposClient(params, base_uri=base_uri)


def _get_start_cursor():
    # Get current saved cursor value
    setup_connection(get_database())
    start_cursor = (
        SubscriptionState.select()
        .where(SubscriptionState.service == SERVICE_DID)
        .execute()[0]
        .cursor
    )
    if start_cursor:
        if not isinstance(start_cursor, int):
            teardown_connection(get_database())
            raise ValueError(f"Saved cursor with value '{start_cursor}' is invalid.")
        return start_cursor

    # If there isn't one, then make sure the DB has a cursor
    logger.info("Generating a cursor for the first time...")
    SubscriptionState.create(service=SERVICE_DID, cursor=0)
    teardown_connection(get_database())
    return None


def _is_client_too_slow_error(e):
    xrpc_error = e.args[0]
    return isinstance(xrpc_error, XrpcError) and xrpc_error.error == "ConsumerTooSlow"
