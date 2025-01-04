"""Main components of the firehose. Functions here handle multiprocessing, running a
firehose client and post processor on separate subprocesses.
"""

import time
from astrofeed_firehose.manager import FirehoseProcessingManager


if __name__ == "__main__":
    print("Initializing firehose processing manager!")
    manager = FirehoseProcessingManager()

    print("Starting child subprocesses")
    manager.start_processes()

    try:
        print("Starting continuous monitoring of processes")
        time.sleep(5)  # Give it a sec to start up
        manager.monitor()

    except KeyboardInterrupt:
        print("Keyboard interrupt - stopping processes.")
        manager.stop_processes()
