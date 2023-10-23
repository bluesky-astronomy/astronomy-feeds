import peewee
from .accounts import AccountList

def get_posts(db: peewee.MySqlDatabase, account_list: AccountList, feed_name: str) -> list:
    pass