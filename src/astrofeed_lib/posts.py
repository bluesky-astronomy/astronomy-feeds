"""Tools for handling lists of posts in the database."""

from .database import Post, get_database, setup_connection, teardown_connection
import time
from datetime import datetime, timedelta
from typing import Final

QUERY_INTERVAL: Final[int] = 24 * 60 * 60
ONE_WEEK_IN_DAYS: Final[int] = 7


class PostQuery:
    def __init__(
        self,
        max_post_age: timedelta = timedelta(days=ONE_WEEK_IN_DAYS),
    ) -> None:
        """Generic refreshing post list."""
        self.last_query_time = time.time()
        self.posts = set()
        self.max_post_age = max_post_age
        self.query_database = self.query_database

    def query_database(self) -> None:
        setup_connection(get_database())
        self.posts = self.post_query()
        teardown_connection(get_database())

    def post_query(self):
        """Intended to be overwritten! Should return a set of posts."""
        return {
            post.uri
            for post in Post.select().where(
                Post.indexed_at > datetime.now() - self.max_post_age  # type: ignore
            )
        }

    def get_posts(self) -> set:
        self.query_database()
        return self.posts

    def add_posts(self, posts):
        for post in posts:
            self.posts.add(post)

    def remove_posts(self, posts):
        for post in posts:
            self.posts.remove(post)


class CachedPostQuery(PostQuery):
    def __init__(
        self,
        query_interval: int = QUERY_INTERVAL,
        max_post_age: timedelta = timedelta(days=ONE_WEEK_IN_DAYS),
    ) -> None:
        """Generic refreshing post list. Uses caching to try to reduce number of
        required query operations!
        """
        super().__init__(max_post_age=max_post_age)
        self.query_interval = query_interval
        self.last_query_time = time.time()

    def get_posts(self) -> set:
        is_overdue = time.time() - self.last_query_time > self.query_interval
        if is_overdue or len(self.posts) == 0:
            self.query_database()
            self.last_query_time = time.time()
        return self.posts
