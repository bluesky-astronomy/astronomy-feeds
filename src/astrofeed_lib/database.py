from datetime import datetime

import peewee
from .config import DatabaseConfig


# Local DB:
# db = peewee.SqliteDatabase('feed_database.db')
# print(DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD)

# MySQL DB:
DATABASE_CONFIG = DatabaseConfig()
db = peewee.MySQLDatabase(DATABASE_CONFIG.name, **DATABASE_CONFIG.params)


class BaseModel(peewee.Model):
    class Meta:
        database = db


# Todo should set attributes based on feeds / have some way to add new columns to the mysql db
class Post(BaseModel):
    indexed_at = peewee.DateTimeField(default=datetime.now, index=True)
    uri = peewee.CharField(index=True)
    cid = peewee.CharField(index=True)
    author = peewee.CharField()
    text = peewee.CharField()
    feed_all = peewee.BooleanField(default=False)
    feed_astro = peewee.BooleanField(default=False)
    feed_exoplanets = peewee.BooleanField(default=False)
    # reply_parent = peewee.CharField(null=True, default=None)
    # reply_root = peewee.CharField(null=True, default=None)


class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.IntegerField()


class Account(BaseModel):
    handle = peewee.CharField(index=True)
    submission_id = peewee.CharField()
    did = peewee.CharField(default="not set")
    is_valid = peewee.BooleanField()
    feed_all = peewee.BooleanField(default=False)  # Also implicitly includes allowing feed_astro
    indexed_at = peewee.DateTimeField(default=datetime.now)


if db.is_closed():
    db.connect()
    db.create_tables([Post, SubscriptionState, Account])
    if not db.is_closed():
        db.close()
