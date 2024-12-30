import peewee
from datetime import datetime
from pathlib import Path
from .config import BLUESKY_DATABASE, ASTROFEED_PRODUCTION


def _check_database_variable():
    if BLUESKY_DATABASE is None:
        raise ValueError(
            "You must set the BLUESKY_DATABASE environment variable to use the "
            "Astronomy feed databases. If ASTROFEED_PRODUCTION is unset (i.e. False), "
            "then this env var should be a path to a local SQLite dev database; if it "
            "is set (i.e. True), then this variable should be set to a MySQL database "
            "connection string."
        )


def _get_mysql_database() -> peewee.MySQLDatabase:
    """Generates a MySQL database connection based on pre-set environment variable.
    This function expects a string that looks like this:
    mysql://USER:PASSWORD@HOST:PORT/NAME?ssl-mode=REQUIRED
    """
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

    return peewee.MySQLDatabase(
        database_name,
        user=user,
        password=password,
        host=host,
        port=port,
        ssl_disabled=ssl_disabled,
    )


def _get_sqlite_database() -> peewee.SqliteDatabase:
    """Generates a local SQLite database connection based on pre-set environment
    variable.
    """
    _check_database_variable()
    
    # Check that the path seems to make sense
    path_to_database = Path(BLUESKY_DATABASE)  # type: ignore
    if not path_to_database.exists():
        raise ValueError(f"Unable to find an SQLite database at {path_to_database}")

    return peewee.SqliteDatabase(BLUESKY_DATABASE)


if ASTROFEED_PRODUCTION:
    db = _get_mysql_database()
else:
    db = _get_sqlite_database()


class BaseModel(peewee.Model):
    class Meta:
        database = db


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


if db.is_closed():
    db.connect()
    db.create_tables([Post, SubscriptionState, Account, BotActions, ModActions])
    if not db.is_closed():
        db.close()
