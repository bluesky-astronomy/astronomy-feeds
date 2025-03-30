import signal
from threading import Thread, Event
from typing import Final

from flask import Flask, jsonify, request, Response

from astrofeed_lib import config, logger
from astrofeed_lib.algorithm import (
    get_posts,
    get_feed_logs_by_feed,
    get_feed_logs_by_date,
    get_feed_stats,
)
from astrofeed_lib.database import get_database, setup_connection, teardown_connection
from astrofeed_server.auth import AuthorizationError, validate_auth
from astrofeed_server.request_log import request_log

# Haven't yet worked out how to get a local Flask debug with VS Code to like a relative
# import, and how to get a Gunicorn running server on Digital Ocean to not *need* one =(
# TODO: make this less of a hack
try:
    from .pinned import add_pinned_post_to_feed
except ModuleNotFoundError:
    from astrofeed_server.pinned import add_pinned_post_to_feed

_FEED_LOG_RETURN_LIMIT: Final[int] = 50

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
        link = (
            f'<li><a href="/xrpc/app.bsky.feed.getFeedSkeleton?feed={uri}">{name}</a>'
        )
        if name in config.FEED_TERMS:
            if config.FEED_TERMS[name] is None:
                terms = "all posts by validated users"
            else:
                terms = ", ".join(
                    config.FEED_TERMS[name]["emoji"] + config.FEED_TERMS[name]["words"]
                )
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
                {
                    "id": "#bsky_fg",
                    "type": "BskyFeedGenerator",
                    "serviceEndpoint": f"https://{config.HOSTNAME}",
                }
            ],
        }
    )


@app.route("/xrpc/app.bsky.feed.describeFeedGenerator", methods=["GET"])
def describe_feed_generator():
    feeds = [{"uri": uri} for uri in config.FEED_URIS.values()]
    response = {
        "encoding": "application/json",
        "body": {"did": config.SERVICE_DID, "feeds": feeds},
    }
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

        request_log.add_request(
            feed=feed,
            limit=limit,
            is_scrolled=cursor is not None,
            user_did=requester_did,
            # , request_host=request.headers.get("Host")
            # , request_referer=request.headers.get("Referer")
            # , request_user_agent=request.headers.get("User-Agent")
        )

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


@app.route("/api/app.getFeedList", methods=["GET"])
# http://127.0.0.1:5000//api/app.getFeedList
def get_feed_list():
    try:
        body: Response = jsonify(config.FEED_TERMS)
    except:
        return "Unsupported algorithm", 404
    return body


@app.route("/api/app.getFeedStats", methods=["GET"])
def get_feed_stats():
    feed_uri = request.args.get("feed", default=None, type=str)
    year = request.args.get("year", default=0, type=int)
    month = request.args.get("month", default=0, type=int)
    day = request.args.get("day", default=0, type=int)
    hour = request.args.get("hour", default=-1, type=int)
    day_of_week = request.args.get("day_of_week", default=-1, type=int)

    # Check that the feed is configured
    if feed_uri != "all":
        if feed_uri not in config.FEED_URIS:
            return "Unsupported algorithm", 400
        feed = config.FEED_URIS[feed_uri]
    else:
        feed = "all"

    try:
        body = get_feed_stats(
            feed=feed,
            year=year,
            month=month,
            day=day,
            hour=hour,
            day_of_week=day_of_week,
        )
    finally:
        pass
    return jsonify(body)


@app.route("/api/app.getFeedLog", methods=["GET"])
# http://127.0.0.1:5000/api/app.getFeedLog?feed=at://did:plc:jcoy7v3a2t4rcfdh6i4kza25/app.bsky.feed.generator/radio&limit=10
def get_feed_log():
    feed_uri = request.args.get("feed", default=None, type=str)
    limit = request.args.get("limit", default=_FEED_LOG_RETURN_LIMIT, type=int)

    # Check that the feed is configured
    if feed_uri not in config.FEED_URIS:
        return "Unsupported algorithm", 400
    feed = config.FEED_URIS[feed_uri]

    try:
        body = get_feed_logs_by_feed(feed, limit)
    finally:
        pass
    return jsonify(body)


@app.route("/api/app.getFeedLogByDate", methods=["GET"])
# http://127.0.0.1:5000//api/app.getFeedLogByDate?date=2025-03-21&limit=10
def get_feed_log_by_date():
    date = request.args.get("date", default=None, type=str)
    limit = request.args.get("limit", default=_FEED_LOG_RETURN_LIMIT, type=int)
    try:
        body = get_feed_logs_by_date(date, limit)
    except ValueError:
        return "Ensure the Date is in YYYY-MM-DD format", 400
    return jsonify(body)


def dump_log_to_db(stop_event: Event = None):
    while stop_event is None or not stop_event.is_set():
        request_log.dump_to_database()
        # instead of time.sleep(x), which will block for x seconds before allowing a kill signal to execute the rest
        # of the method, use the wait method on Event. This allows the "pause" to be interrupted and the rest of the
        # method to be executed for cleanup
        # https://stackoverflow.com/questions/5114292/break-interrupt-a-time-sleep-in-python
        stop_event.wait(60)
    # one last dump of the logs to the DB so we don't lose the last minute worth of logs
    logger.info("One last request log dump to DB before shutting down")
    request_log.dump_to_database()


# Schedule the job to dump the in-memory log of requests to the database to run every 1 minute
log_dumper_stop_event: Event = Event()
log_dumper: Thread = Thread(target=dump_log_to_db, args=(log_dumper_stop_event,))
log_dumper.start()


def shutdown_handler(signum, frame):
    logger.warn("Shutting down Flask server...")
    # Perform cleanup tasks here, e.g., closing database connections,
    # releasing resources, etc.
    if not get_database().is_closed():
        teardown_connection(get_database())
    # set stop event on the log dumper thread so it can clean up gracefully before exiting
    log_dumper_stop_event.set()
    exit(0)


# this is outside the "if __name__ == "__main__"" since using gunicorn doesn't seem to call this module as main, and this
# code needs to run
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == "__main__":
    app.run(debug=True)
