from flask import Flask, jsonify, request
import schedule
from threading import Event, Thread
import time
import signal
from astrofeed_lib import config
from astrofeed_lib.database import get_database, setup_connection, teardown_connection
from astrofeed_lib.algorithm import get_posts, get_feed_logs
from astrofeed_lib import logger
from astrofeed_server.request_log import request_log
from astrofeed_server.auth import AuthorizationError, validate_auth


# Haven't yet worked out how to get a local Flask debug with VS Code to like a relative
# import, and how to get a Gunicorn running server on Digital Ocean to not *need* one =(
# TODO: make this less of a hack
try: 
    from .pinned import add_pinned_post_to_feed
except ModuleNotFoundError:
    from astrofeed_server.pinned import add_pinned_post_to_feed


app = Flask(__name__)


# This hook ensures that a connection is opened to handle any queries
# generated by the request.
@app.before_request
def _db_connect():
    if get_database().is_closed():
        setup_connection(get_database())


# This hook ensures that the connection is closed when we've finished
# processing the request.
@app.teardown_request
def _db_close(exc):
    if not get_database().is_closed():
        teardown_connection(get_database())


@app.route("/")
def index():
    feed_urls = []

    for uri, name in config.FEED_URIS.items():
        link = f"<li><a href=\"/xrpc/app.bsky.feed.getFeedSkeleton?feed={uri}\">{name}</a>"
        if name in config.FEED_TERMS:
            if config.FEED_TERMS[name] is None:
                terms = "all posts by validated users"
            else:
                terms = ', '.join(config.FEED_TERMS[name]["emoji"] + config.FEED_TERMS[name]["words"])
            feed_urls.append(link + f" ({terms})</li>")
        else:
            feed_urls.append(link + " (feed for moderation purposes)</li>")

    feed_urls = "\n".join(feed_urls)

    return f"""<b>This server is the endpoint of astronomy feeds on Bluesky.</b>
        <br><br>
        The following feeds are available on this server:
        <ul>
        {feed_urls}
        </ul>
        
        To be able to post in a feed, visit <a href="https://signup.astronomy.blue">signup.astronomy.blue</a>.
        <br><br>
        Please report any issues on <a href="https://github.com/bluesky-astronomy">GitHub</a>.
        <br><br>
        Other endpoints:
        <ul>
        <li><a href="/.well-known/did.json">/.well-known/did.json</a></li>
        <li><a href="/xrpc/app.bsky.feed.describeFeedGenerator">/xrpc/app.bsky.feed.describeFeedGenerator</a></li>
        <li><a href="/xrpc/app.bsky.feed.getFeedLog?feed=at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/astro-all">/xrpc/app.bsky.feed.getFeedLog?feed=at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/astro-all</a></li>
        </ul>
        """


@app.route("/.well-known/did.json", methods=["GET"])
def did_json():
    if not config.SERVICE_DID.endswith(config.HOSTNAME):
        return "", 404

    return jsonify(
        {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": config.SERVICE_DID,
            "service": [
                {"id": "#bsky_fg", "type": "BskyFeedGenerator", "serviceEndpoint": f"https://{config.HOSTNAME}"}
            ],
        }
    )


@app.route("/xrpc/app.bsky.feed.describeFeedGenerator", methods=["GET"])
def describe_feed_generator():
    feeds = [{"uri": uri} for uri in config.FEED_URIS.values()]
    response = {"encoding": "application/json", "body": {"did": config.SERVICE_DID, "feeds": feeds}}
    return jsonify(response)


@app.route("/xrpc/app.bsky.feed.getFeedSkeleton", methods=["GET"])
def get_feed_skeleton():
    feed_uri = request.args.get("feed", default=None, type=str)

    # Check that the feed is configured
    if feed_uri not in config.FEED_URIS:
        return "Unsupported algorithm", 400
    feed = config.FEED_URIS[feed_uri]

    requester_did = get_requester_did()

    # Query the algorithm
    try:
        cursor = request.args.get("cursor", default=None, type=str)
        limit = request.args.get("limit", default=20, type=int)
        logger.debug(f"request for {feed} with cursor {cursor} and limit {limit}")
        #req: _RequestLog = _RequestLog()
        request_log.add_request(feed=feed, limit=limit, is_scrolled=cursor is not None, user_did=requester_did
                        , request_host=request.headers.get("Host")
                        , request_referer=request.headers.get("Referer")
                        , request_user_agent=request.headers.get("User-Agent"))

        body = get_posts(feed, cursor, limit)
    # except ValueError:
    #     return "Malformed cursor", 400
    finally:
        pass

    # Add pinned instruction post
    # See: https://bsky.app/profile/did:plc:jcoy7v3a2t4rcfdh6i4kza25/post/3kc632qlmnm2j
    if cursor is None:
        add_pinned_post_to_feed(body)

    return jsonify(body)


def get_requester_did():
    try:
        requester_did = validate_auth(request)
    except AuthorizationError:
        requester_did = "Unknown"
    return requester_did


@app.route("/xrpc/app.bsky.feed.getFeedLog", methods=["GET"])
def get_feed_log():
    feed_uri = request.args.get("feed", default=None, type=str)

    # Check that the feed is configured
    if feed_uri not in config.FEED_URIS:
        return "Unsupported algorithm", 400
    feed = config.FEED_URIS[feed_uri]

    try:
        body = get_feed_logs(feed)
    finally:
        pass
    return jsonify(body)


def dump_log_to_db():
    logger.info("Dumping log to DB")
    request_log.dump_to_database()


def run_continuously(interval:int = 1) -> Event:
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = Event()

    class ScheduleThread(Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


def shutdown_handler(signum, frame):
    logger.warn("Shutting down Flask server...")
    # Perform cleanup tasks here, e.g., closing database connections,
    # releasing resources, etc.
    # Stop the background thread
    stop_run_continuously.set()
    if not get_database().is_closed():
        teardown_connection(get_database())
    #one last dump of the logs to the DB so we don't lose the last minute
    dump_log_to_db()
    exit(0)

# this is outside the "if __name__ == "__main__" since using gunicorn doesn't call this module as main, and this
# code needs to run
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)
# Schedule the job to dump the in-memory log of requests to the database to run every 1 minute
schedule.every(1).minutes.do(dump_log_to_db)
# Start the background thread
stop_run_continuously = run_continuously()

if __name__ == "__main__":
    app.run(debug=True)
