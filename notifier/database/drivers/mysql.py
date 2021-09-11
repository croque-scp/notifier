import json
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, Tuple, Type, Union, cast

import pymysql
from pymysql.constants.CLIENT import MULTI_STATEMENTS
from pymysql.cursors import SSDictCursor

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.utils import BaseDatabaseWithSqlFileCache
from notifier.secretgetter import get_secret
from notifier.types import (
    CachedUserConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
)


class MySqlDriver(BaseDatabaseDriver, BaseDatabaseWithSqlFileCache):
    """Database powered by MySQL."""

    def __init__(self, database_name=":memory:"):
        BaseDatabaseDriver.__init__(self, database_name)
        BaseDatabaseWithSqlFileCache.__init__(self)

        # Parameters for the connection are kept as secrets
        mysql_host = get_secret("mysql", "notifier_host")
        if not mysql_host:
            raise ValueError("MySQL host address is not configured")
        mysql_username = get_secret("mysql", "notifier_username")
        if not mysql_username:
            raise ValueError("MySQL username is not configured")
        mysql_password = get_secret("mysql", "notifier")
        if not mysql_password:
            raise ValueError("MySQL password is not configured")

        self.conn = pymysql.connect(
            host=mysql_host,
            user=mysql_username,
            password=mysql_password,
            database=None if database_name == ":memory:" else database_name,
            # Cursor is accessible like a dict, and is unbuffered (i.e.
            # retrieves rows from the server one-by-one, using less
            # memory). However, any pending data must be purged from the
            # connection (by calling cursor.close) before it can be reused.
            cursorclass=SSDictCursor,
            # Autocommit except during explicit transactions
            autocommit=True,
            # Enable 'executescript'-like functionality for all statements
            client_flag=MULTI_STATEMENTS,
        )

    @contextmanager
    def transaction(self) -> Iterator[SSDictCursor]:
        """Context manager for an explicit transaction.

        Any error will cause pending changes to be rolled back; otherwise,
        changes will be committed at the end of the context.
        """
        cursor = self.conn.cursor()
        self.conn.begin()
        try:
            yield cursor
            self.conn.commit()
        except:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def execute_named(
        self, query_name: str, params: Iterable = None
    ) -> SSDictCursor:
        """Execute a named query against the database. The query is read
        either from file or the cache.

        :param query_name: The name of the query to execute, which must
        have a corresponding SQL file.
        :param params: SQL parameters to pass to the query.
        :returns: The resultant cursor of the query.
        """
        self.cache_named_query(query_name)
        query = self.query_cache[query_name]["query"]
        cursor = self.conn.cursor()
        if self.query_cache[query_name]["script"]:
            if params is not None:
                raise ValueError("Script does not accept params")
            return cursor.execute(query)
        return cursor.execute(query, {} if params is None else params)


def __instantiate():
    """Raises a typing error if the driver has missing methods.

    Remove after class is finished.
    """
    MySqlDriver()
