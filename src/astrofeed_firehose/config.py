import os
from typing import Final

# Fetch base URI
BASE_URI: Final[str] = "wss://bsky.network/xrpc"  # Which relay to fetch commits from

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
