"""Main components of the firehose. Functions here handle multiprocessing, running a
firehose client and post processor on separate subprocesses.
"""
import time
from astrofeed_firehose.manager import FirehoseProcessingManager


if __name__ == "__main__":
    manager = FirehoseProcessingManager()
    manager.start_processes()
    time.sleep(5)  # Give it a sec to start up
    manager.monitor()
