import peewee
from peewee import DatabaseProxy
from datetime import datetime
from pathlib import Path
from .config import BLUESKY_DATABASE, ASTROFEED_PRODUCTION
from playhouse.pool import PooledMySQLDatabase
from astrofeed_lib import logger

proxy: DatabaseProxy | None = None


def _check_database_variable():
    if BLUESKY_DATABASE is None:
        raise ValueError(
            "You must set the BLUESKY_DATABASE environment variable to use the "
            "Astronomy feed databases. If ASTROFEED_PRODUCTION is unset (i.e. False), "
            "then this env var should be a path to a local SQLite dev database; if it "
            "is set (i.e. True), then this variable should be set to a MySQL database "
            "connection string."
        )


def _get_mysql_database() -> PooledMySQLDatabase:
    """Generates and/or grabs a MySQL database connection from the pool based on pre-set environment variable.
    This function expects a string that looks like this:
    mysql://USER:PASSWORD@HOST:PORT/NAME?ssl-mode=REQUIRED
    """
    logger.debug("Getting a Pooled MySQL Database")
    _check_database_variable()

    # Todo can this be neater? May just be worth changing the env variable spec anyway, as the current format is a pain to process. May be a good to-do for when we migrate fully to new hosting.
    # 1. Split it into three segments
    connection_string = BLUESKY_DATABASE.replace("mysql://", "")  # type: ignore
    first_half, second_half = connection_string.split("/")
    user_details, host_details = first_half.split("@")

    # 2. Deal with user & host
    user, password = user_details.split(":")
    host, port = host_details.split(":")
    port = int(port)

    # 3. Deal with name and flags
    database_name, flags = second_half.split("?")
    ssl_disabled = True
    if "ssl-mode=REQUIRED" in flags:
        ssl_disabled = False

    return PooledMySQLDatabase(
        database_name,
        max_connections=10,
        stale_timeout=None,
        timeout=5,
        user=user,
        password=password,
        host=host,
        port=port,
        ssl_disabled=ssl_disabled,
        autoconnect=False,
    )


def _get_sqlite_database() -> peewee.SqliteDatabase:
    """Generates a local SQLite database connection based on pre-set environment
    variable. Not using pooled connections because SQLite doesn't seem to play well with
    threads, and since this is just for running locally, not putting the time into figuring
    it out now
    """
    logger.debug("Getting a Pooled SQLite Database")
    _check_database_variable()

    # Check that the path seems to make sense
    path_to_database: Path = Path(BLUESKY_DATABASE)
    if not path_to_database.exists():
        logger.error(f"Unable to find an SQLite database at {path_to_database}")
        raise ValueError(f"Unable to find an SQLite database at {path_to_database}")

    """
    Would like to be able to use the PooledSqlliteDatabase, but this class doesn't like to be instantiated on one thread
    and then accessed on another thread
    return PooledSqliteDatabase(BLUESKY_DATABASE, autoconnect=False)
    """
    return peewee.SqliteDatabase(BLUESKY_DATABASE, autoconnect=False)


def get_database() -> DatabaseProxy:
    """
    Method used to grab a connection to the SQL Database. Handles checking if running in local vs. production
    mode, and connecting to the appropriate database.

    MySQL Database proxy is a wrapper around a connection pool - calling open and close will grab a connection from
    the pool, or return a connection to the pool
    """
    global proxy

    if proxy is None:
        logger.debug("Need to instantiate a new database...")
        if ASTROFEED_PRODUCTION:
            logger.info("Production - grabbing the proxy to the MySql database")
            db = _get_mysql_database()
        else:
            logger.info("Local environment - grabbing a proxy to the SQLite database")
            db = _get_sqlite_database()
        proxy = DatabaseProxy()
        proxy.initialize(db)

    return proxy


def setup_connection(database: DatabaseProxy) -> None:
    if database is None:
        raise Exception(
            "Database Proxy is uninitialized - please pass a valid Database Proxy to "
            "setup_connection"
        )

    if database.is_closed():
        logger.debug("Connecting to DB")
        database.connect()
    else:
        logger.error(
            "Exception setting up connection: database connection is already open"
        )


def teardown_connection(database: DatabaseProxy) -> None:
    logger.debug("Closing DB connection")
    if database is not None and not database.is_closed():
        try:
            database.close()
        except Exception as ex:
            logger.error(f"Exception trying to close DB connection {ex}")


class DBConnection(object):
    def __init__(self):
        global proxy
        proxy = get_database()

    def __enter__(self):
        global proxy
        if proxy is not None and proxy.is_closed():
            proxy.connect()
        return proxy

    def __exit__(self, type, value, traceback):
        global proxy
        teardown_connection(proxy)


class BaseModel(peewee.Model):
    class Meta:
        database = get_database()


class Post(BaseModel):
    indexed_at = peewee.DateTimeField(default=datetime.utcnow, index=True)
    uri = peewee.CharField(index=True)
    cid = peewee.CharField(index=True)
    author = peewee.CharField(index=True)
    text = peewee.CharField()
    hidden = peewee.BooleanField(index=True, default=False)  # New column 24/12/30

    # Feed booleans
    # Main feeds
    feed_all = peewee.BooleanField(default=False, index=True)
    feed_astro = peewee.BooleanField(default=False, index=True)
    feed_astrophotos = peewee.BooleanField(default=False, index=True)

    # Astronomy topics
    feed_cosmology = peewee.BooleanField(default=False, index=True)
    feed_exoplanets = peewee.BooleanField(default=False, index=True)
    feed_extragalactic = peewee.BooleanField(default=False, index=True)
    feed_highenergy = peewee.BooleanField(default=False, index=True)
    feed_instrumentation = peewee.BooleanField(default=False, index=True)
    feed_methods = peewee.BooleanField(default=False, index=True)
    feed_milkyway = peewee.BooleanField(default=False, index=True)
    feed_planetary = peewee.BooleanField(default=False, index=True)
    feed_radio = peewee.BooleanField(default=False, index=True)
    feed_stellar = peewee.BooleanField(default=False, index=True)

    # Astrononmy / other
    feed_education = peewee.BooleanField(default=False, index=True)
    feed_history = peewee.BooleanField(default=False, index=True)

    # feed_moderation = peewee.BooleanField(default=False)
    # reply_parent = peewee.CharField(null=True, default=None)
    # reply_root = peewee.CharField(null=True, default=None)


class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.BigIntegerField()


class Account(BaseModel):
    handle = peewee.CharField(index=True)
    did = peewee.CharField(default="not set", index=True)
    indexed_at = peewee.DateTimeField(default=datetime.utcnow, index=True)

    # Account flags
    is_valid = peewee.BooleanField(index=True)
    is_muted = peewee.BooleanField(index=True, default=False)  # New column 24/12/30
    is_banned = peewee.BooleanField(index=True, default=False)  # New column 24/12/30

    # Counts on number of mod actions taken against this account
    hidden_count = peewee.IntegerField(default=0)  # New column 24/12/30
    warned_count = peewee.IntegerField(default=0)  # New column 24/12/30
    muted_count = peewee.IntegerField(default=0)  # New column 24/12/30
    banned_count = peewee.IntegerField(default=0)  # New column 24/12/30

    # Whether or not account is a mod
    mod_level = peewee.IntegerField(null=False, index=True, unique=False, default=0)

    # Deprecated columns
    # Todo remove eventually - will need to be removed from the db first though
    feed_all = peewee.BooleanField(default=False)
    submission_id = peewee.CharField()


class BotActions(BaseModel):
    indexed_at = peewee.DateTimeField(default=datetime.utcnow, index=True)
    did = peewee.CharField(default="not set")
    type = peewee.CharField(null=False, default="unrecognized", index=True)
    stage = peewee.CharField(
        null=False, default="initial", index=True
    )  # Initial: command initially sent but not replied to
    parent_uri = peewee.CharField(null=False, default="")
    parent_cid = peewee.CharField(null=False, default="")
    latest_uri = peewee.CharField(null=False, default="")
    latest_cid = peewee.CharField(null=False, default="")
    complete = peewee.BooleanField(null=False, default=False, index=True)
    authorized = peewee.BooleanField(null=False, index=True, default=True)
    checked_at = peewee.DateTimeField(null=False, index=True, default=datetime.utcnow)


class ModActions(BaseModel):
    indexed_at = peewee.DateTimeField(default=datetime.utcnow, index=True)
    did_mod = peewee.CharField(index=True, null=False)
    did_user = peewee.CharField(index=True)
    action = peewee.CharField(index=True, null=False)
    expiry = peewee.DateTimeField(index=True, null=True)


# class Signups(BaseModel):
#     did = peewee.CharField(index=True)
#     status = peewee.CharField(index=True)
#     uri = peewee.CharField()
#     cid = peewee.CharField()

with DBConnection() as conn:
    conn.create_tables([Post, SubscriptionState, Account, BotActions, ModActions])
