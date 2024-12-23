import peewee
from peewee import DatabaseProxy
from datetime import datetime
from pathlib import Path
from .config import BLUESKY_DATABASE, ASTROFEED_PRODUCTION
from playhouse.pool import PooledMySQLDatabase
from icecream import ic

# set up icecream
ic.configureOutput(includeContext=True)

proxy: DatabaseProxy = None


def _check_database_variable():
    if BLUESKY_DATABASE is None:
        raise ValueError(
            "You must set the BLUESKY_DATABASE environment variable to use the "
            "Astronomy feed databases. If ASTROFEED_PRODUCTION is unset (i.e. False), "
            "then this env var should be a path to a local SQLite dev database; if it "
            "is set (i.e. True), then this variable should be set to a MySQL database "
            "connection string."
        )


def _get_mysql_database() -> PooledMySQLDatabase: # peewee.MySQLDatabase:
    """Generates a MySQL database connection based on pre-set environment variable.
    This function expects a string that looks like this:
    mysql://USER:PASSWORD@HOST:PORT/NAME?ssl-mode=REQUIRED
    """
    ic("Getting MySQL Database")
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

    """
    return peewee.MySQLDatabase(
        database_name,
        user=user,
        password=password,
        host=host,
        port=port,
        ssl_disabled=ssl_disabled,
    )
    """
    return PooledMySQLDatabase(
        database_name,
        max_connection=10,
        stale_timeout=None,
        timeout=5,
        user=user,
        password=password,
        host=host,
        port=port,
        ssl_disabled=ssl_disabled,
        autoconnect=False
    )


def _get_sqlite_database() -> peewee.SqliteDatabase:
    """Generates a local SQLite database connection based on pre-set environment
    variable. Not using pooled connections because SQLite doesn't seem to play well with
    threads, and since this is just for running locally, not putting the time into figuring
    it out now
    """
    ic("Getting SQLite Database")
    _check_database_variable()
    
    # Check that the path seems to make sense
    path_to_database = Path(BLUESKY_DATABASE)  # type: ignore
    if not path_to_database.exists():
        ic(f"Unable to find an SQLite database at {path_to_database}")
        raise ValueError(f"Unable to find an SQLite database at {path_to_database}")

    return peewee.SqliteDatabase(BLUESKY_DATABASE, autoconnect=False)
"""
    return PooledSqliteDatabase(
        BLUESKY_DATABASE,
        max_connections=1,
        stale_timeout=None,
        timeout=5
    )
"""


def get_database() -> DatabaseProxy:
    """
    Method used to grab a connection to the SQL Database. Handles checking if running in local vs. production
    mode, and connecting to the appropriate database.

    MySQL Database proxy is a wrapper around a connection pool - calling open and close will
    """
    global proxy

    if proxy is None:
        ic("Need to instantiate a new database...")
        if ASTROFEED_PRODUCTION:
            ic("Production - grabbing the proxy to the MySql database")
            db = _get_mysql_database()
        else:
            ic("Local environment - grabbing a connection to the SQLite database")
            db = _get_sqlite_database()
        proxy = DatabaseProxy()
        proxy.initialize(db)

    return proxy


def setup_connection(database: DatabaseProxy) -> None:
    ic("Connecting to DB")
    if database.is_closed():
        ic("Opening new connection")
        database.connect()


def teardown_connection(database: DatabaseProxy) -> None:
    ic("Closing DB connection")
    if not database.is_closed():
        database.close()


class BaseModel(peewee.Model):
    class Meta:
        database = get_database()


class Post(BaseModel):
    indexed_at = peewee.DateTimeField(default=datetime.utcnow, index=True)
    uri = peewee.CharField(index=True)
    cid = peewee.CharField(index=True)
    author = peewee.CharField(index=True)
    text = peewee.CharField()

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
    submission_id = peewee.CharField()
    did = peewee.CharField(default="not set", index=True)
    is_valid = peewee.BooleanField(index=True)
    feed_all = peewee.BooleanField(
        default=False
    )  # Also implicitly includes allowing feed_astro
    indexed_at = peewee.DateTimeField(default=datetime.utcnow, index=True)
    mod_level = peewee.IntegerField(null=False, index=True, unique=False, default=0)


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

"""
if get_database().is_closed():
    get_database().connect()
    get_database().create_tables([Post, SubscriptionState, Account, BotActions, ModActions])
    if not get_database().is_closed():
        get_database().close()
"""
setup_connection(get_database())
get_database().create_tables([Post, SubscriptionState, Account, BotActions, ModActions])
teardown_connection(get_database())