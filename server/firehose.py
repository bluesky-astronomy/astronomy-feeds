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
        'posts': {'created': [], 'deleted': []},
        'reposts': {'created': [], 'deleted': []},
        'likes': {'created': [], 'deleted': []},
        'follows': {'created': [], 'deleted': []},
    }

    # Try to decode
    # print("commit.repo: ", commit.repo)
    # print("commit.ops: ", commit.ops)
    # print("commit.blocks: ", commit.blocks)
    # try:
    #     car = CAR.from_bytes(commit.blocks)
    # except Exception as e:
    #     logger.info("EXCEPTION while attempting to decode commit.blocks")
    #     traceback.print_exception(e)
    #     print("commit.repo: ", commit.repo)
    #     print("commit.ops: ", commit.ops)
    #     print("commit.blocks: ", commit.blocks)
    #     car = None

    if commit.blocks == b'' or len(commit.ops) == 0:
        return operation_by_type
    car = CAR.from_bytes(commit.blocks)

    for op in commit.ops:
        uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')

        if op.action == 'update':
            # not supported yet
            continue

        if op.action == 'create' and car is not None:
            if not op.cid:
                continue

            create_info = {'uri': str(uri), 'cid': str(op.cid), 'author': commit.repo}

            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            record = get_or_create(record_raw_data, strict=False)
            if uri.collection == ids.AppBskyFeedPost and is_record_type(record, ids.AppBskyFeedPost):
                operation_by_type['posts']['created'].append({'record': record, **create_info})

            # The following types of event don't need to be tracked by the feed right now, and are removed.
            # elif uri.collection == ids.AppBskyFeedLike and is_record_type(record, ids.AppBskyFeedLike):
            #     operation_by_type['likes']['created'].append({'record': record, **create_info})
            # elif uri.collection == ids.AppBskyFeedRepost and is_record_type(record, ids.AppBskyFeedRepost):
            #     operation_by_type['reposts']['created'].append({'record': record, **create_info})
            # elif uri.collection == ids.AppBskyGraphFollow and is_record_type(record, ids.AppBskyGraphFollow):
            #     operation_by_type['follows']['created'].append({'record': record, **create_info})

        if op.action == 'delete':
            if uri.collection == ids.AppBskyFeedPost:
                operation_by_type['posts']['deleted'].append({'uri': str(uri)})

            # The following types of event don't need to be tracked by the feed right now.
            # elif uri.collection == ids.AppBskyFeedLike:
            #     operation_by_type['likes']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyFeedRepost:
            #     operation_by_type['reposts']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == ids.AppBskyGraphFollow:
            #     operation_by_type['follows']['deleted'].append({'uri': str(uri)})

    return operation_by_type


def _worker_loop(receiver, cursor, update_cursor_in_database=True):
    logger.info("-> Firehose worker process started")
    while True:
        # Wait for the multiprocessing.connection.Connection to contain something. This is blocking, btw!
        message = receiver.recv()

        commit = parse_subscribe_repos_message(message)
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            continue
        
        # Update stored state every ~100 events
        if commit.seq % 100 == 0:
            cursor.value = commit.seq
            # x = time.time()
            if update_cursor_in_database:
                db.connect(reuse_if_open=True)  # Todo: not sure if needed
                SubscriptionState.update(cursor=commit.seq).where(SubscriptionState.service == SERVICE_DID).execute()
            else:
                logger.info(f"Cursor: {commit.seq}")
            # db.close()
            # print(time.time() - x)

        operations_callback(_get_ops_by_type(commit), commit.seq)

        # ops = _get_ops_by_type(commit)
        # for post in ops['posts']['created']:
        #     post_msg = post['record'].text
        #     post_langs = post['record'].langs
        #     print(f'New post in the network! Langs: {post_langs}. Text: {post_msg}')


def worker_main(receiver, cursor, update_cursor_in_database=True, dump_posts_on_fail=False) -> None:
    """Main worker handler! Automatically reboots when done."""
    reboots = 0
    while True:
        try:
            _worker_loop(receiver, cursor, update_cursor_in_database=update_cursor_in_database)
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
        logger.info(f"Reboot count: {reboots}")


def run(stream_stop_event=None):
    """Continually the firehose and processes posts from on the network."""
    while True:
        # Run the firehose! (_run is the main function here)
        try:
            _run(stream_stop_event=stream_stop_event)

        # Try to handle ConsumerTooSlow exceptions. These can happen if the network is very busy or if there's a bad
        # internet connection. In this case, we'll try to just restart the firehose.
        except FirehoseError as e:
            if e.args:
                xrpc_error = e.args[0]
                if isinstance(xrpc_error, XrpcError) and xrpc_error.error == 'ConsumerTooSlow':
                    logger.warn('Reconnecting to Firehose due to ConsumerTooSlow...')
                    continue

            raise e


def _run(stream_stop_event=None):
    print(f"Running firehose for {SERVICE_DID}")

    # Get initial cursor value
    start_cursor = SubscriptionState.get(SubscriptionState.service == SERVICE_DID).cursor
    params = None
    cursor = multiprocessing.Value('i', 0)
    if start_cursor:
        if start_cursor is not None:
            params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=start_cursor)
            cursor = multiprocessing.Value('i', start_cursor)
        else:
            print("Saved cursor was invalid!", start_cursor)

    # If there isn't one, then set one up
    if not start_cursor:
        print("Generating a cursor for the first time...")
        SubscriptionState.create(service=SERVICE_DID, cursor=0)

    # Optionally, manually set a cursor
    # params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=376765400)
    
    # This is the client used to subscribe to the firehose from the atproto lib.
    client = FirehoseSubscribeReposClient(params, base_uri="wss://bsky.network/xrpc")  # )

    # Setup workers to analyse and process posts (i.e. this is done as separately as possible to atproto post ingestion)
    # TODO: multi-workers are currently NOT supported! Only 1 worker is allowed at this time.
    #       There are too many things that need to be thread-safed for it to get implemented right now...
    #       Also: AWS doesn't support Queue and Pool objects, so it takes a lot more manual coding (sad.)
    receiver, pipe = multiprocessing.Pipe(duplex=False)
    worker = multiprocessing.Process(
        target=worker_main, args=(receiver, cursor), kwargs=dict(update_cursor_in_database=True)
    )

    # The handler below tells the client what to do when a new commit is encountered
    def on_message_handler(message: MessageFrame) -> None:
        pipe.send(message)

        # Update local client cursor value
        if cursor.value:
            current_cursor = cursor.value
            cursor.value = 0
            client.update_params(models.ComAtprotoSyncSubscribeRepos.Params(cursor=current_cursor))

    worker.start()
    client.start(on_message_handler)
