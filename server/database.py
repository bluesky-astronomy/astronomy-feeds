from datetime import datetime

import peewee
from .config import DATABASE_NAME, DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_PORT


# db = peewee.SqliteDatabase('feed_database.db')
# print(DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD)
db = peewee.MySQLDatabase(
    DATABASE_NAME,
    host=DATABASE_HOST,
    port=int(DATABASE_PORT),
    user=DATABASE_USER,
    password=DATABASE_PASSWORD,
    # ssl_ca="/home/emily/ca-certificate.crt",
    ssl_disabled=False,
)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    author = peewee.CharField()
    text = peewee.CharField()
    feed_all = peewee.BooleanField(default=False)
    feed_astro = peewee.BooleanField(default=False)
    # reply_parent = peewee.CharField(null=True, default=None)
    # reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.now)


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
