import logging
from .config import ASTROFEED_PRODUCTION, DEBUG_ENABLED

# set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if ASTROFEED_PRODUCTION is False or DEBUG_ENABLED is True else logging.WARN) # OR check if a debug flag is set for production
logging.basicConfig(format='%(asctime)s %(name)s - [%(levelname)s] : %(message)s')