import logging
import time
from atproto import models
from server.database import db, Post, Account
from .config import QUERY_INTERVAL


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AccountList:
    def __init__(self) -> None:
        self.accounts = None
        self.last_query_time = time.time()

    def _query_database(self) -> None:
        if db.is_closed():
            db.connect()

        self.accounts = {account.did for account in Account.select()}

        if not db.is_closed():
            db.close()
    
    def get_accounts(self) -> set:
        is_overdue = time.time() - self.last_query_time > QUERY_INTERVAL
        if is_overdue or self.accounts is None:
            self._query_database()
        return self.accounts
    

account_list = AccountList()


def operations_callback(ops: dict) -> None:
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync

    # for example, let's create our custom feed that will contain all posts that contains alf related text

    posts_to_create = []
    valid_dids = account_list.get_accounts()
    valid_posts = [post for post in ops['posts']['created'] if post['author'] in valid_dids]

    for created_post in valid_posts:
        post_dict = {
            'uri': created_post['uri'],
            'cid': created_post['cid'],
            'author': created_post['author'],
            'feed_all': True,
            'feed_astro': True
            # 'reply_parent': reply_parent,
            # 'reply_root': reply_root,
        }
        posts_to_create.append(post_dict)

    posts_to_delete = [post['uri'] for post in ops['posts']['deleted']]
    if posts_to_delete:
        Post.delete().where(Post.uri.in_(posts_to_delete))
        # logger.info(f'Deleted from feed: {len(posts_to_delete)}')

    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added to feed: {len(posts_to_create)}')
