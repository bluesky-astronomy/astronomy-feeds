"""Commit processing components that work through posts and decide if they need to be
added to the feeds.
"""
import logging
import time
from atproto import CAR, AtUri
from atproto.xrpc_client.models import get_or_create, ids, is_record_type
from atproto.firehose import parse_subscribe_repos_message
from atproto.xrpc_client import models
from astrofeed_lib.config import SERVICE_DID
from astrofeed_lib.database import SubscriptionState, db
from server.data_filter import operations_callback


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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

            record = get_or_create(record_raw_data, strict=False)
            if uri.collection == ids.AppBskyFeedPost and is_record_type(
                record,  # type: ignore
                ids.AppBskyFeedPost,
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


def _process_posts(receiver, cursor, worker_time, update_cursor_in_database=True):
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


def run_post_processor(
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
            _process_posts(
                receiver,
                cursor,
                worker_time,
                update_cursor_in_database=update_cursor_in_database,
            )
        except Exception:
            logger.exception(
                "Post processing worker encountered an exception while processing a "
                "post! This post will be skipped."
            )

        # Optionally clear the pipe so that the next worker doesn't get swamped
        if dump_posts_on_fail:
            logger.info("Clearing out connection to parent thread")
            messages_dumped = 0
            while receiver.poll():
                receiver.recv()
                messages_dumped += 1
            logger.info(f"Lost {messages_dumped} messages")

        reboots += 1
        logger.info(f"Worker reboot count: {reboots}")
