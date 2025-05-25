"""Tools for handling lists of accounts and working with Bluesky DIDs etc."""

from .database import Account
from .database import (
    DBConnection,
)  # get_database, setup_connection, teardown_connection
import time


class AccountQuery:
    def __init__(self, flags=None) -> None:
        """Generic refreshing account list. Will return all accounts that have flags
        matching the defined 'flags' parameter.
        """
        self.accounts = None
        self.flags = flags
        self.query_database = self.query_database
    
    def get_accounts(self) -> set:
        """Fetches accounts given the query defined in self.account_query."""
        self.query_database()
        return self.accounts  # type ignore because pylance is a silly thing here. this should always be a set

    def query_database(self) -> None:
        """Performs the actual database query step to fetch things."""
        with DBConnection():
            self.accounts = self.account_query()

    def account_query(self):
        """OVERWRITE ME IF SUBCLASSING. Returns a set of accounts."""
        query = Account.select()
        if self.flags is not None:
            query = query.where(*self.flags)
        return {account.did for account in query}



class CachedAccountQuery(AccountQuery):
    def __init__(
        self,
        flags=None,
        query_interval: int = 60 * 60 * 24,
    ) -> None:
        """Generic refreshing account list. Will return all accounts that have flags
        matching the defined 'flags' parameter.
        """
        super().__init__(flags=flags)
        self.query_interval = query_interval
        self.last_query_time = time.time()

    def get_accounts(self) -> set:
        """Fetches accounts given the query defined in self.account_query.
        
        The result of this query is cached for the length of time defined by
        query_interval when initiating this class. By default, it's 24 hours.
        """
        is_overdue = time.time() - self.last_query_time > self.query_interval
        if is_overdue or self.accounts is None:
            self.query_database()
            self.last_query_time = time.time()
        return self.accounts  # type ignore because pylance is a silly thing here. this should always be a set


class CachedModeratorList(CachedAccountQuery):
    def account_query(self):
        return get_moderators()

    def get_accounts_above_level(self, minimum_level: int) -> set[str]:
        """Wraps get_accounts and returns only moderators with the desired minimum
        level.
        """
        return {
            did for did, level in self.get_accounts().items() if level >= minimum_level
        }


class CachedBannedList(CachedAccountQuery):
    def account_query(self):
        return get_banned_accounts()


def get_moderators() -> dict[str, int]:
    """Returns a dict containing the DIDs of all current moderators as keys and their
    mod level as values.
    """
    query = Account.select(Account.did, Account.mod_level).where(Account.mod_level >= 1)  # type: ignore
    return {user.did: user.mod_level for user in query.execute()}


def get_banned_accounts() -> set[str]:
    """Returns a set containing the DIDs of all banned accounts."""
    query = Account.select(Account.did).where(Account.is_banned)
    return {user.did for user in query.execute()}
