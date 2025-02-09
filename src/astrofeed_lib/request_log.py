from astrofeed_lib import logger
import datetime


class _Request:
    request_dt: datetime
    request_feed_uri: str
    request_limit: int
    request_is_scrolled: bool
    request_user_did: str

    def __str__(self):
        return f"Request_dt: {self.request_dt}"


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

    def add_request(self, feed: str, limit: int, is_scrolled: bool, user_did: str) -> None:
        logger.info("Adding request to log")
        request: _Request = _Request()
        request.request_dt = datetime.datetime.utcnow()
        request.request_limit = limit
        request.request_is_scrolled = is_scrolled
        request.request_user_did = user_did
        request.request_feed_uri = feed
        self.log.append(request)
