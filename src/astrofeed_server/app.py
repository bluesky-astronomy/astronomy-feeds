from flask import Flask, jsonify, request
from astrofeed_lib import config
from astrofeed_lib.database import get_database, setup_connection, teardown_connection
from astrofeed_lib.algorithm import get_posts, get_feed_logs
from astrofeed_lib import logger
from astrofeed_lib.request_log import _RequestLog

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

    # Get the user's DID
    # try:
    #     authorization = request.headers['Authorization']
    # except Exception as e:
    #     authorization = None
    #     print("Authorization not in request header!")

    # if authorization is not None:

    # Query the algorithm
    try:
        cursor = request.args.get("cursor", default=None, type=str)
        limit = request.args.get("limit", default=20, type=int)
        logger.info(f"request for {feed} with cursor {cursor} and limit {limit}")
        req: _RequestLog = _RequestLog()
        req.add_request(feed=feed, limit=limit, is_scrolled=cursor is not None, user_did=""
                        , request_host=request.headers.get("Host")
                        , request_referer=request.headers.get("Referer")
                        , request_user_agent=request.headers.get("User-Agent"))
        # logger.info(f"full request log: {req}")
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


if __name__ == "__main__":
    app.run(debug=True)
