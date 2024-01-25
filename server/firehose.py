"""Main components of the firehose. Functions here handle multiprocessing, running a
firehose client and post processor on separate subprocesses.
"""
import multiprocessing
import logging
import time
from server.client import run_client
from server.post_processor import run_post_processor


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _create_shared_resources():
    """Creates resources that are shared between subprocesses."""
    cursor = multiprocessing.Value("i", 0)
    client_time = multiprocessing.Value("d", time.time())
    post_time = multiprocessing.Value("d", time.time())
    receiver, pipe = multiprocessing.Pipe(duplex=False)
    return cursor, client_time, post_time, receiver, pipe


def _start_client_worker(cursor, pipe, latest_firehose_event_time):
    """Starts the client worker that connects to the Bluesky network."""
    logger.info("Starting new firehose client worker...")
    client_worker = multiprocessing.Process(
        target=run_client,
        args=(cursor, pipe, latest_firehose_event_time),
        name="Client worker",
    )
    client_worker.start()
    return client_worker


def _start_post_worker(cursor, receiver, latest_worker_event_time):
    """Starts the post processing worker."""
    logger.info("Starting new post processing worker...")
    post_worker = multiprocessing.Process(
        target=run_post_processor,
        args=(receiver, cursor, latest_worker_event_time),
        kwargs=dict(update_cursor_in_database=True),
        name="Post processing worker",
    )
    post_worker.start()
    return post_worker


def _start_workers():
    """Starts all workers used by the firehose."""
    cursor, client_time, post_time, receiver, pipe = _create_shared_resources()
    client_worker = _start_client_worker(cursor, pipe, client_time)
    post_worker = _start_post_worker(cursor, receiver, post_time)

    # Return stuff that the watchdog will need to check
    return post_worker, client_worker, client_time, post_time


def _stop_workers(post_worker, client_worker):
    """Tries to kill child processes."""
    try:
        post_worker.kill()
    except Exception:
        pass
    try:
        client_worker.kill()
    except Exception:
        pass


def run(watchdog_interval=300, startup_sleep=10):
    """Continually runs the firehose and processes posts from on the network.

    Incorporates watchdog functionality, which checks that all worker subprocesses are
    still running once every watchdog_interval seconds. The firehose will stop if this
    happens.
    """
    start_time = time.time()
    post_worker, client_worker, client_time, post_time = _start_workers()

    # We wait a bit for our first check. This should be enough time for the system to
    # start and get settled.
    time.sleep(startup_sleep)

    # Continually check that subprocesses are behaving nicely.
    while True:
        current_time = time.time()

        # Checks
        errors = []
        if not client_worker.is_alive():
            errors.append("-> RuntimeError: Client worker died.")
        if client_time.value < current_time - watchdog_interval:  # type: ignore
            errors.append("-> RuntimeError: Client worker hung.")
        if not post_worker.is_alive():
            errors.append("-> RuntimeError: Post worker died.")
        if post_time.value < current_time - watchdog_interval:  # type: ignore
            errors.append("-> RuntimeError: Post worker hung.")

        # Stop firehose if necessary
        if errors:
            break

        time.sleep(watchdog_interval)

    _stop_workers(post_worker, client_worker)

    # Raise overall error
    uptime = time.time() - start_time
    raise RuntimeError(
        "Firehose workers encountered critical errors and appear to be non-functioning."
        " The watchdog will now stop the firehose. Worker errors: \n"
        + "\n".join(errors)
        + f"\nTotal uptime was {uptime/60**2/24:.3f} days ({uptime:.0f} seconds)."
    )
