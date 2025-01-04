import os
from typing import Final

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
CPU_COUNT: Final[int] = int(_cpu_count)


# ------------------------
# SPECIFIC SETTINGS
# These settings probably won't need tweaking and aren't exposed as environment
# variables, but could be necessary to change in the future or on different machines
# ------------------------
# Buffer size of the internal process queue (I think it's in bytes?)
# N.B.: one commit is about ~1-2 KB
# The last multiple is size in MB
QUEUE_BUFFER_SIZE = 1024**2 * 10

# How often the watchdog should check that all processes are running (in seconds)
MANAGER_CHECK_INTERVAL = 60
