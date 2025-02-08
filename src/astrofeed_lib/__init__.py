import logging
from .config import ASTROFEED_PRODUCTION, DEBUG_ENABLED

# set up logging
logger = logging.getLogger(__name__)

# Decide on minimum logging level to log.
_logging_level = logging.INFO
if DEBUG_ENABLED or ASTROFEED_PRODUCTION is False:
    _logging_level = logging.DEBUG

# Set logging format. 
# In production, the logging system captures timestamps, service name & logging level, so these aren't needed in the log.
_logging_format = '%(asctime)s %(name)s - [%(levelname)s] : %(message)s'
if ASTROFEED_PRODUCTION:
    _logging_format = '[%(levelname)s] : %(message)s'

logger.setLevel(_logging_level)
logging.basicConfig(format=_logging_format)
