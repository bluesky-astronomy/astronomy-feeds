from datetime import datetime
from typing import Optional

from server import config
from server.database import Post, Account
from ._algorithm import Algorithm


algorithm = Algorithm(config.URI_ASTRO_ALL)
