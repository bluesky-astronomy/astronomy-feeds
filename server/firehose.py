import multiprocessing

from atproto import CAR, AtUri
from atproto.firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from atproto.firehose.models import MessageFrame
from atproto.xrpc_client import models
from atproto.xrpc_client.models import get_or_create, ids, is_record_type
from atproto.exceptions import FirehoseError
from atproto.xrpc_client.models.common import XrpcError

from server.data_filter import operations_callback
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState, db

import logging
import traceback
import time


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> dict:  # noqa: C901
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

    car = CAR.from_bytes(commit.blocks)

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

            record = get_or_create(record_raw_data, strict=False)
            if uri.collection == ids.AppBskyFeedPost and is_record_type(
                record, ids.AppBskyFeedPost
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
            if uri.collection == ids.AppBskyFeedPost:
                operation_by_type["posts"]["deleted"].append({"uri": str(uri)})

            # The following types of event don't need to be tracked by the feed right now.
            # elif uri.collection == ids.AppBskyFeedLike:
            #     operation_by_type['likes']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyFeedRepost:
            #     operation_by_type['reposts']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyGraphFollow:
            #     operation_by_type['follows']['deleted'].append({'uri': str(uri)})

    return operation_by_type


def _worker_loop(receiver, cursor, worker_time, update_cursor_in_database=True):
    logger.info("... post processing worker started")
    while True:
        # Wait for the multiprocessing.connection.Connection to contain something. This is blocking, btw!
        message = receiver.recv()

        commit = parse_subscribe_repos_message(message)
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            continue

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
        operations_callback(_get_ops_by_type(commit), commit.seq)
        worker_time.value = time.time()


def worker_main(
    receiver,
    cursor,
    worker_time,
    update_cursor_in_database=True,
    dump_posts_on_fail=False,
) -> None:
    """Main worker handler!

    Currently, on an exception when handling a post, the worker will restart (skipping
    that post). This should be very rare.
    """
    reboots = 0
    while True:
        try:
            _worker_loop(
                receiver,
                cursor,
                worker_time,
                update_cursor_in_database=update_cursor_in_database,
            )
        except Exception as e:  # Todo: not good to catch all but it will do I guess
            logger.info(f"EXCEPTION IN FIREHOSE WORKER: {e}")
            traceback.print_exception(e)

        # Clear the pipe so that the next worker doesn't get swamped
        if dump_posts_on_fail:
            logger.info("Clearing out connection to parent thread")
            messages_dumped = 0
            while receiver.poll():
                receiver.recv()
                messages_dumped += 1
            logger.info(f"Lost {messages_dumped} messages")

        reboots += 1
        logger.info(f"Worker reboot count: {reboots}")


def get_start_cursor():
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


def get_client(
    start_cursor: int | None = None, base_uri: str = "wss://bsky.network/xrpc"
):
    if start_cursor is None:
        start_cursor = get_start_cursor()
    params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=start_cursor)
    return FirehoseSubscribeReposClient(params, base_uri=base_uri)


def start_firehose():
    # Initialise shared resources/pipes
    cursor = multiprocessing.Value("i", 0)
    client_time = multiprocessing.Value("d", time.time())
    post_time = multiprocessing.Value("d", time.time())
    receiver, pipe = multiprocessing.Pipe(duplex=False)

    # Start subprocesses
    client_worker = start_client_worker(cursor, pipe, client_time)
    post_worker = start_post_worker(cursor, receiver, post_time)

    # Return stuff that the watchdog will need to check
    return (
        post_worker,
        client_worker,
        client_time,
        post_time,
    )


def stop_firehose(post_worker, client_worker, errors, start_time):
    # Kill child processes
    try:
        post_worker.kill()
    except Exception as e:
        pass
    try:
        client_worker.kill()
    except Exception as e:
        pass

    uptime = time.time() - start_time

    # Raise overall error
    raise RuntimeError(
        "Firehose workers encountered critical errors and appear to be non-functioning."
        " The watchdog will now stop the firehose. Worker errors: \n"
        + "\n".join(errors)
        + f"\nTotal uptime was {uptime/60**2/24:.3f} days ({uptime:.0f} seconds)."
    )


def start_post_worker(cursor, receiver, latest_worker_event_time):
    logger.info("Starting new post processing worker...")
    post_worker = multiprocessing.Process(
        target=worker_main,
        args=(receiver, cursor, latest_worker_event_time),
        kwargs=dict(update_cursor_in_database=True),
        name="Post processing worker",
    )
    post_worker.start()
    return post_worker


def start_client_worker(cursor, pipe, latest_firehose_event_time):
    logger.info("Starting new firehose client worker...")
    client_worker = multiprocessing.Process(
        target=client_main,
        args=(cursor, pipe, latest_firehose_event_time),
        name="Client worker",
    )
    client_worker.start()
    return client_worker


def run(watchdog_interval=30, startup_sleep=10):
    """Continually runs the firehose and processes posts from on the network.

    Incorporates watchdog functionality, which checks that all worker subprocesses are
    still running once every watchdog_interval seconds. The firehose will stop if this
    happens.
    """
    start_time = time.time()
    post_worker, client_worker, client_time, post_time = start_firehose()
    # We wait a bit for our first check. This should be enough time for the system to
    # start and get settled.
    time.sleep(startup_sleep)

    while True:
        current_time = time.time()

        # Checks
        errors = []
        if not client_worker.is_alive():
            errors.append("-> RuntimeError: Client worker died.")
        if client_time.value < current_time - watchdog_interval:
            errors.append("-> RuntimeError: Client worker hung.")
        if not post_worker.is_alive():
            errors.append("-> RuntimeError: Post worker died.")
        if post_time.value < current_time - watchdog_interval:
            errors.append("-> RuntimeError: Post worker hung.")

        # Restart if necessary
        if errors:
            stop_firehose(post_worker, client_worker, errors, start_time)
        
        time.sleep(watchdog_interval)


def _is_client_too_slow_error(e):
    xrpc_error = e.args[0]
    return isinstance(xrpc_error, XrpcError) and xrpc_error.error == "ConsumerTooSlow"


def client_main(cursor, pipe, firehose_time):
    # The handler below tells the client what to do when a new commit is encountered
    def on_message_handler(message: MessageFrame) -> None:
        pipe.send(message)

        # Update local client cursor value
        if cursor.value:
            current_cursor = cursor.value
            cursor.value = 0
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=current_cursor)
            )
        firehose_time.value = time.time()

    while True:
        client = get_client()
        try:
            logger.info("... firehose client worker started")
            client.start(on_message_handler)
        except FirehoseError as e:
            if not _is_client_too_slow_error(e):
                raise e
            logger.warn("Reconnecting to Firehose due to ConsumerTooSlow...")
            continue
