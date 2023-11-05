import logging
from astrofeed_lib.database import db, Post
from astrofeed_lib.accounts import AccountList
from astrofeed_lib.feeds import post_in_feeds
import time
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
    

account_list = AccountList(with_database_closing=True)
account_list.get_accounts()  # Initial get


class PostList:
    def __init__(
            self, 
            with_database_closing: bool=False, 
            query_interval: int=60*60*24, 
            max_post_age: timedelta=timedelta(days=7)
        ) -> None:
        """Generic refreshing post list. Tries to reduce number of required query operations!"""
        self.last_query_time = time.time()
        self.query_interval = query_interval
        self.posts = None
        self.max_post_age = max_post_age
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
        return {uri for uri in Post.select(Post.uri).where(Post.indexed_at > datetime.now() - self.max_post_age)}

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
    

post_list = PostList(with_database_closing=True)
post_list.get_posts()  # Initial get


def operations_callback(ops: dict) -> None:
    # See how many posts are valid
    posts_to_create = []
    valid_dids = account_list.get_accounts()
    valid_posts = [post for post in ops['posts']['created'] if post['author'] in valid_dids]

    # Classify valid posts into feed categories
    feed_counts = None
    for created_post in valid_posts:
        # Basic post info to add to the database
        post_text = created_post['record']['text']
        post_dict = {
            'uri': created_post['uri'],
            'cid': created_post['cid'],
            'author': created_post['author'],
            'text': post_text,
        }

        # Add labels to the post for
        feed_labels = post_in_feeds(post_text)
        post_dict.update(feed_labels)
        posts_to_create.append(post_dict)

        # Count how many posts we have
        if feed_counts is None:
            feed_counts = {key: 0 for key in feed_labels}
        for a_key in feed_labels:
            feed_counts[a_key] += feed_labels[a_key]

    # See if there are any posts that need deleting
    posts_to_delete = [post['uri'] for post in ops['posts']['deleted'] if post['uri'] in post_list.get_posts()]

    # Perform database operations
    if posts_to_delete or posts_to_create:
        db.connect(reuse_if_open=True)

        if posts_to_delete:
            Post.delete().where(Post.uri.in_(posts_to_delete))
            post_list.remove_posts(posts_to_delete)
            logger.info(f'Deleted posts: {len(posts_to_delete)}')

        if posts_to_create:
            with db.atomic():
                for post_dict in posts_to_create:
                    Post.create(**post_dict)
            post_list.add_posts([x['uri'] for x in posts_to_create])
            feed_counts_string = ", ".join([f"{key[5:]}-{feed_counts[key]}" for key in feed_counts])
            logger.info(f'Added posts: {feed_counts_string}')

        db.close()
