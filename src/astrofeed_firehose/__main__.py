"""Main components of the firehose. Functions here handle multiprocessing, running a
firehose client and post processor on separate subprocesses.
"""

import time
from astrofeed_firehose.manager import FirehoseProcessingManager
from astrofeed_lib import logger


if __name__ == "__main__":
    logger.info("Initializing firehose processing manager!")
    manager = FirehoseProcessingManager()

    logger.info("Starting child subprocesses")
    manager.start_processes()

    try:
        logger.info("Starting continuous monitoring of processes")
        time.sleep(10)  # Give it a sec to start up
        manager.monitor()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt - stopping processes.")
        manager.stop_processes()
