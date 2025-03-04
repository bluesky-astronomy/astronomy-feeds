from astrofeed_lib import logger
from astrofeed_lib.database import ActivityLog, DBConnection
import datetime


class _Request:
    request_id: int
    request_dt: datetime
    request_feed_uri: str
    request_limit: int
    request_is_scrolled: bool
    request_user_did: str
    request_host: str
    request_referer: str
    request_user_agent: str

    def __str__(self):
        return (f"REQUEST-------\n"
                f"Requst_id: {self.request_id}\n"
                f"Request_dt: {self.request_dt}\n"
                f"Request_feed_uri: {self.request_feed_uri}\n"
                f"Request_limit: {self.request_limit}\n"
                f"Request_is_scrolled: {self.request_is_scrolled}\n"
                f"Request_user_did: {self.request_user_did}\n"
                f"Request_host: {self.request_host}\n"
                f"Request_referer: {self.request_referer}\n"
                f"Request_user_agent: {self.request_user_agent}")


class _RequestLog:
    _self = None
    log: list[_Request] = None

    def __new__(cls):
        if cls._self is None:
            cls._self = super().__new__(cls)
        return cls._self

    def __init__(self):
        if self.log is None:
            self.log: list[_Request] = []

    def __str__(self) -> str:
        ret_str: str = ""
        for req in self.log:
            ret_str += str(req)
        return ret_str

    def add_request(self, feed: str, limit: int, is_scrolled: bool, user_did: str, request_host: str,
                    request_referer: str, request_user_agent: str) -> None:
        logger.debug("Adding request to collection")
        request: _Request = _Request()
        request.request_dt = datetime.datetime.utcnow()
        request.request_limit = limit
        request.request_is_scrolled = is_scrolled
        request.request_user_did = user_did
        request.request_feed_uri = feed
        request.request_referer = request_referer
        request.request_host = request_host
        request.request_user_agent = request_user_agent
        self.log.append(request)

        # want to move this call to save to the DB off-thread
        #self.dump_to_database()

    def dump_to_database(self) -> None:
        with DBConnection() as conn:
            for req in self.log:
                log: ActivityLog = ActivityLog()
                log.request_dt = req.request_dt
                log.request_host = req.request_host
                log.request_referer = req.request_referer
                log.request_limit = req.request_limit
                log.request_is_scrolled = req.request_is_scrolled
                log.request_user_agent = req.request_user_agent
                log.request_feed_uri = req.request_feed_uri
                log.request_user_did = req.request_user_did
                log.save()
        self.log = []