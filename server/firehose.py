import typing as t

from atproto import CAR, AtUri, models
from atproto.firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from atproto.xrpc_client.models.utils import get_or_create, is_record_type

from server.data_filter import operations_callback
from server.database import SubscriptionState, db
from server import config

import logging
import traceback

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

if t.TYPE_CHECKING:
    from atproto.firehose import MessageFrame


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> dict:  # noqa: C901
    operation_by_type = {
        'posts': {'created': [], 'deleted': []},
        'reposts': {'created': [], 'deleted': []},
        'likes': {'created': [], 'deleted': []},
        'follows': {'created': [], 'deleted': []},
    }

    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')

        if op.action == 'update':
            # not supported yet
            continue

        if op.action == 'create':
            if not op.cid:
                continue

            create_info = {'uri': str(uri), 'cid': str(op.cid), 'author': commit.repo}

            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            record = get_or_create(record_raw_data, strict=False)
            if uri.collection == models.ids.AppBskyFeedPost and is_record_type(record, models.AppBskyFeedPost):
                operation_by_type['posts']['created'].append({'record': record, **create_info})
            # The following types of event don't need to be tracked by the feed right now:
            # elif uri.collection == models.ids.AppBskyFeedLike and is_record_type(record, models.AppBskyFeedLike):
            #     operation_by_type['likes']['created'].append({'record': record, **create_info})
            # elif uri.collection == models.ids.AppBskyGraphFollow and is_record_type(record, models.AppBskyGraphFollow):
            #     operation_by_type['follows']['created'].append({'record': record, **create_info})

        if op.action == 'delete':
            if uri.collection == models.ids.AppBskyFeedPost:
                operation_by_type['posts']['deleted'].append({'uri': str(uri)})
            # The following types of event don't need to be tracked by the feed right now:
            # elif uri.collection == models.ids.AppBskyFeedLike:
            #     operation_by_type['likes']['deleted'].append({'uri': str(uri)})
            # elif uri.collection == models.ids.AppBskyGraphFollow:
            #     operation_by_type['follows']['deleted'].append({'uri': str(uri)})

    return operation_by_type


def on_error_callback(e):
    logger(f"Exception encountered in on_message_handler! {e}")
    traceback.print_exc()

    logger("Trying to re-open database connection (as this is a common issue...)")
    if db.is_closed():
        db.connect()


def run(stream_stop_event=None):
    name = config.SERVICE_DID
    state = SubscriptionState.select(SubscriptionState.service == name).first()
    print(f"Running firehose from HOSTNAME {name} and resuming at state {state}")

    params = None
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)

    client = FirehoseSubscribeReposClient(params)

    if not state:
        SubscriptionState.create(service=name, cursor=0)

    def on_message_handler(message: 'MessageFrame') -> None:
        # stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        commit = parse_subscribe_repos_message(message)
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            return

        # update stored state every ~20 events
        if commit.seq % 20 == 0:
            if db.is_closed():
                db.connect()
            SubscriptionState.update(cursor=commit.seq).where(SubscriptionState.service == name).execute()

        operations_callback(_get_ops_by_type(commit))

    client.start(on_message_handler, on_error_callback)
