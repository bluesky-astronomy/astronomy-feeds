"""Standard algorithm formats for feeds on the server."""
from ..accounts import AccountList
from server.database import Post, Account
from typing import Optional
from datetime import datetime


def account_function_only_valid():
    """Basic account selection function that only posts those that are valid."""
    return Account.select(Account.did).where(Account.is_valid)


class Algorithm:
    def __init__(self, uri, account_selection_function=None) -> None:
        self.account_list = AccountList(with_database_closing=False)
        self.uri = uri

        # Optionally, overwrite how self.account_list selects accounts
        if account_selection_function is None:
            account_selection_function = account_function_only_valid
        
        self.account_list.account_query = account_selection_function

    def get_accounts(self):
        return self.account_list.get_accounts()

    def select_posts(self, valid_dids, limit):
        return (Post
            .select()
            .where(Post.author.in_(valid_dids))
            .order_by(Post.indexed_at.desc())
            .limit(limit)
        )
    
    def create_feed(self, posts):
        """Turns list of posts into a sorted """
        return [{'post': post.uri} for post in posts]
    
    def _handle_cursor(self, cursor, posts):
        """Handles cursor operations if one is included in the request"""
        cursor_parts = cursor.split('::')
        if len(cursor_parts) != 2:
            raise ValueError('Malformed cursor')
        indexed_at, cid = cursor_parts
        indexed_at = datetime.fromtimestamp(int(indexed_at) / 1000)
        posts = posts.where(Post.indexed_at <= indexed_at).where(Post.cid < cid)
        return posts
    
    def _move_cursor_to_last_post(self, posts):
        last_post = posts[-1] if posts else None
        if last_post:
            return f'{int(last_post.indexed_at.timestamp() * 1000)}::{last_post.cid}'
        return None

    def handler(self, cursor: Optional[str], limit: int) -> dict:
        valid_dids = self.get_accounts()
        posts = self.select_posts(valid_dids, limit)

        if cursor:
            posts = self._handle_cursor(cursor, posts)

        feed = self.create_feed(posts)
        cursor = self._move_cursor_to_last_post(posts)

        return {
            'cursor': cursor,
            'feed': feed
        }



    
