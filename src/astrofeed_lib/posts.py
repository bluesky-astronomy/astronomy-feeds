"""Tools for handling lists of posts in the database."""
from astrofeed_lib.database import db, Post
import time
from datetime import datetime, timedelta


class PostList:
    def __init__(
        self,
        with_database_closing: bool = False,
        query_interval: int = 60 * 60 * 24,
        max_post_age: timedelta = timedelta(days=7),
    ) -> None:
        """Generic refreshing post list. Tries to reduce number of required query operations!"""
        self.last_query_time = time.time()
        self.query_interval = query_interval
        self.posts = set()
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
        return {
            post.uri
            for post in Post.select().where(
                Post.indexed_at > datetime.now() - self.max_post_age
            )
        }

    def get_posts(self) -> set:
        is_overdue = time.time() - self.last_query_time > self.query_interval
        if is_overdue or len(self.posts) == 0:
            self.query_database()
            self.last_query_time = time.time()
        return self.posts

    def add_posts(self, posts):
        for post in posts:
            self.posts.add(post)

    def remove_posts(self, posts):
        for post in posts:
            self.posts.remove(post)
