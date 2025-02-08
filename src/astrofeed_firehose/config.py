import os
from typing import Final
# from astrofeed_lib import logger


# ------------------------
# GENERAL SETTINGS
# ------------------------
# Fetch base URI
BASE_URI: Final[str] = os.getenv(
    "FIREHOSE_BASE_URI", "wss://bsky.network/xrpc"
)  # Which relay to fetch commits from

# Fetch cursor override
_cursor_override = os.getenv("FIREHOSE_CURSOR_OVERRIDE", None)
if _cursor_override is not None:
    _cursor_override = int(_cursor_override)
CURSOR_OVERRIDE: Final[int | None] = _cursor_override

# Assign number of CPUs
_cpu_count = os.getenv("FIREHOSE_WORKER_COUNT", os.cpu_count())
if _cpu_count is None:
    _cpu_count = 1
_cpu_count = int(_cpu_count)
if _cpu_count < 1:
    _cpu_count = 1
CPU_COUNT: Final[int] = _cpu_count


# ------------------------
# SPECIFIC SETTINGS
# These settings probably won't need tweaking and aren't exposed as environment
# variables, but could be necessary to change in the future or on different machines
# ------------------------

# OVERALL MANAGER -----------------------
# How often the watchdog should check that all processes are running (in seconds)
MANAGER_CHECK_INTERVAL = 60

# QUEUE PRIMITIVE -----------------------
# Buffer size of the internal process queue (I think it's in bytes?)
# N.B.: one commit is about ~1-2 KB
# The last multiple is size in MB
QUEUE_BUFFER_SIZE = 1024**2 * 8

# Number of commits the firehose client should try to send at once.
COMMITS_TO_ADD_AT_ONCE = 100

# Maximum number of commits each processing worker should try to get at once.
COMMITS_TO_FETCH_AT_ONCE = 100

# Sleep times for if the queue is empty or full
FULL_QUEUE_SLEEP_TIME = 0.1
EMPTY_QUEUE_SLEEP_TIME = 0.01

# CURSOR SYNCHRONIZATION ----------------
# How often to update the cursor for the firehose client & in the database
# I.e., on each nth commit we update the cursor in each place
FIREHOSE_CURSOR_UPDATE = 1000  # Todo: see if this can be increased to 1000
DATABASE_CURSOR_UPDATE = (
    10000  # Todo: see if this can be increased to 10000, which is <1 minute of ops/sec
)
