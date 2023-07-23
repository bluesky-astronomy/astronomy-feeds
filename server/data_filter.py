import logging
from server.database import db, Post
from .accounts import AccountList
from .algos.astro import post_is_valid
import time
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
    

account_list = AccountList(with_database_closing=True)


class PostList:
    def __init__(self, with_database_closing=False, query_interval=60*60*24) -> None:
        """Generic refreshing post list. Tries to reduce number of required query operations!"""
        self.last_query_time = time.time()
        self.query_interval = query_interval
        self.posts = None
        if with_database_closing:
            self.query_database = self.query_database_with_closing
        else:
            self.query_database = self.query_database_without_closing

    def query_database_without_closing(self) -> None:
        db.connect(reuse_if_open=True)
        self.posts = self.post_query()

    def query_database_with_closing(self) -> None:
        db.connect(reuse_if_open=True)
        self.posts = self.post_query()
        db.close()

    def post_query(self):
        """Intended to be overwritten! Should return a set of posts."""
        return {uri for uri in Post.select(Post.uri).where(Post.indexed_at > datetime.now() - timedelta(days=7))}

    def get_posts(self) -> set:
        is_overdue = time.time() - self.last_query_time > self.query_interval
        if is_overdue or self.posts is None:
            self.query_database()
            self.last_query_time = time.time()
        return self.posts
    
    def add_posts(self, posts):
        for post in posts:
            self.posts.add(post)

    def remove_posts(self, posts):
        for post in posts:
            self.posts.remove(post)
    

post_list = PostList(with_database_closing=False)


def operations_callback(ops: dict) -> None:
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync

    # for example, let's create our custom feed that will contain all posts that contains alf related text

    posts_to_create = []
    valid_dids = account_list.get_accounts()
    valid_posts = [post for post in ops['posts']['created'] if post['author'] in valid_dids]

    astro_feed_counter = 0
    for created_post in valid_posts:
        post_text = created_post['record']['text']
        add_to_feed_astro = post_is_valid(post_text)
        astro_feed_counter += int(add_to_feed_astro)

        post_dict = {
            'uri': created_post['uri'],
            'cid': created_post['cid'],
            'author': created_post['author'],
            'text': post_text,
            'feed_all': True,
            'feed_astro': add_to_feed_astro,
            # 'reply_parent': reply_parent,
            # 'reply_root': reply_root,
        }
        posts_to_create.append(post_dict)

    posts_to_delete = [post['uri'] for post in ops['posts']['deleted'] if post['uri'] in post_list.get_posts()]

    if posts_to_delete or posts_to_create:

        start_time = time.time()
        db.connect(reuse_if_open=True)
        open_time = time.time()

        if posts_to_delete:
            Post.delete().where(Post.uri.in_(posts_to_delete))
            post_list.remove_posts(posts_to_delete)
            logger.info(f'Deleted from feed: {len(posts_to_delete)}')

        delete_time = time.time()

        if posts_to_create:
            with db.atomic():
                for post_dict in posts_to_create:
                    Post.create(**post_dict)
            post_list.add_posts([x['uri'] for x in posts_to_create])
            logger.info(f'Added to astro-all: {len(posts_to_create)}; astro: {astro_feed_counter}')

        add_time = time.time()

        db.close()

        close_time = time.time()

        close_time -= add_time
        add_time -= delete_time
        delete_time -= open_time
        open_time -= start_time

        logger.info(f'Timing stats:\nopn: {1000 * open_time:.3f}  del: {1000 * delete_time:.3f} add: {1000 * add_time:.3f} clo: {1000 * close_time:.3f}')
