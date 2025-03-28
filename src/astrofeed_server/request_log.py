from dataclasses import dataclass
from astrofeed_lib import logger
from astrofeed_lib.database import ActivityLog, DBConnection
import datetime
import copy
from threading import Lock


@dataclass
class _Request:
    """
    Data class representing an in-memory log of the request to the server for the BlueSky Astronomy Feeds
    """

    request_id: int
    request_dt: datetime
    request_feed_uri: str
    request_limit: int
    request_is_scrolled: bool
    request_user_did: str
    # request_host, request_referer, and user_agent could be logged, but since they are almost always proxied from the
    # BlueSky server, this data is likely meaningless to us
    # request_host: str
    # request_referer: str
    # request_user_agent: str

    def __str__(self):
        return (
            f"REQUEST-------\n"
            f"Request_id: {self.request_id}\n"
            f"Request_dt: {self.request_dt}\n"
            f"Request_feed_uri: {self.request_feed_uri}\n"
            f"Request_limit: {self.request_limit}\n"
            f"Request_is_scrolled: {self.request_is_scrolled}\n"
            f"Request_user_did: {self.request_user_did}\n"
            # f"Request_host: {self.request_host}\n"
            # f"Request_referer: {self.request_referer}\n"
            # f"Request_user_agent: {self.request_user_agent}"
        )


class _RequestLog:
    """
    wrapper class so all threads of the Flask server get a hold of this instance and update the
    request log. A separate job is scheduled from the Flask server to call the 'dump_to_database' method of the class
    on a regular schedule to save the in-memory information to the configured database
    """

    def __init__(self):
        self.log: list[_Request] = []
        self.lock: Lock = Lock()

    def __str__(self) -> str:
        ret_str: str = ""
        for req in self.log:
            ret_str += str(req)
        return ret_str

    def add_request(
        self,
        feed: str,
        limit: int,
        is_scrolled: bool,
        user_did: str,
        # , request_host: str
        # , request_referer: str
        # , request_user_agent: str
    ) -> None:
        """
        Build a _Request object from the input information and add it to the in-memory list of requests for the feed.
        :param feed: BlueSky Astronomy Feed being requested
        :param limit: request limit - usually 20
        :param is_scrolled: whether or not the request is from the user scrolling through the feed, or starting at the top
        :param user_did: the ID of the user on BlueSky making the feed request
        :param request_host: URL of the computer making the request
        :param request_referer: URL of the computer that made the referral to the feed
        :param request_user_agent: browser type
        :return: None
        """
        logger.debug("Adding request to collection")
        request: _Request = _Request(
            request_id=0,
            request_dt=datetime.datetime.utcnow(),
            request_limit=limit,
            request_is_scrolled=is_scrolled,
            request_user_did=user_did,
            request_feed_uri=feed,
            # request_referer=request_referer,
            # request_host=request_host,
            # request_user_agent=request_user_agent,
        )
        with self.lock:
            self.log.append(request)

    def dump_to_database(self) -> None:
        """
        Take the in-memory RequestLog and save it to the database. Lock this action to ensure we don't have another
        thread come in and remove the data out from underneath us. If performance becomes an issue, we can decrease
        the amount of time between job runs so the list does not get too large, making the deepcopy take less time.
        Once the deepcopy is done, control is returned to the program, and the copied list is looped through,
        saving the data to the database table
        :return: None
        """
        logger.info("Dumping log to DB")
        with self.lock:
            # copy the list and clear the old one to avoid losing any data
            temp_log: list[_Request] = copy.deepcopy(self.log)
            self.log = []

        # now go through the copied list and save to the database
        log_to_save: list[ActivityLog] = []
        with DBConnection() as conn:
            for req in temp_log:
                act_log: ActivityLog = ActivityLog(
                    request_dt=req.request_dt,
                    request_limit=req.request_limit,
                    request_is_scrolled=req.request_is_scrolled,
                    request_feed_uri=req.request_feed_uri,
                    request_user_did=req.request_user_did,
                )

                log_to_save.append(act_log)

            with conn.atomic():
                ActivityLog.bulk_create(log_to_save, batch_size=100)


request_log: _RequestLog = _RequestLog()
