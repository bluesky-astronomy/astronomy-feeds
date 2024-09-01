"""Code for client that connects to firehose."""
import logging
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.connection import Connection
import time
from atproto.exceptions import FirehoseError
from atproto import FirehoseSubscribeReposClient
from atproto import firehose_models
from atproto import models
from atproto_client.models.common import XrpcError
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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


def _get_client(
    start_cursor: int | None = None, base_uri: str = "wss://bsky.network/xrpc"
):
    if start_cursor is None:
        start_cursor = _get_start_cursor()
    params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=start_cursor)
    return FirehoseSubscribeReposClient(params, base_uri=base_uri)


def _is_client_too_slow_error(e):
    xrpc_error = e.args[0]
    return isinstance(xrpc_error, XrpcError) and xrpc_error.error == "ConsumerTooSlow"


firehose_start = time.time()
on_message_handler_total = 0.
commits = 0


def run_client(
    cursor: Synchronized,  # Return value of multiprocessing.Value
    pipe: Connection,
    firehose_time: Synchronized,  # Return value of multiprocessing.Value
    start_cursor: int | None = None,
    base_uri: str = "wss://bsky.network/xrpc",
):
    """Primary function for running the client that connects to Bluesky. New commits are
    immediately sent to the separate post processing worker.
    """
    

    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        """This handler tells the client what to do when a new commit is encountered."""
        global firehose_start, on_message_handler_total, commits

        # Send it to post processing worker to handle
        on_message_handler_start = time.time()
        pipe.send(message)
        on_message_handler_finish = time.time()

        # Update local client cursor value
        if cursor.value:
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=cursor.value)
            )
            cursor.value = 0

        # Update current working time so that the watchdog knows this process is running
        firehose_time.value = time.time()

        # TODO: remove benchmarking
        
        
        on_message_handler_total = on_message_handler_total + on_message_handler_finish - on_message_handler_start
        commits = commits + 1
        if commits % 10000 == 0:
            firehose_total = time.time() - firehose_start
            print(on_message_handler_total / firehose_total, firehose_total, on_message_handler_total)

            firehose_start = time.time()
            on_message_handler_total = 0.
        

    # Continually restarts the client if ConsumerTooSlow errors are encountered. This
    # can happen due to the Bluesky network being busy or internet connection issues.
    while True:
        client = _get_client(start_cursor=start_cursor, base_uri=base_uri)

        try:
            logger.info("... firehose client worker started")
            client.start(on_message_handler)

        except FirehoseError as e:
            if not _is_client_too_slow_error(e):
                raise e
            logger.warn("Reconnecting to Firehose due to ConsumerTooSlow...")
