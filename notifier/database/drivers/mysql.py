import json
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Iterable, List, Optional, Tuple, Type, Union, cast

import pymysql
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
            cursorclass=SSDictCursor,
            autocommit=True,
        )

        self.transaction = Transaction(self)


class Transaction(AbstractContextManager):
    """Context manager for an explicit transaction.

    Any error will cause pending changes to be rolled back; otherwise,
    changes will be committed at the end of the context.
    """

    def __init__(self, db: MySqlDriver):
        self.db = db

    def __enter__(self):
        self.db.conn.begin()

    def __exit__(
        self,
        exc_type: Union[Type[BaseException], None],
        exc_value: Union[BaseException, None],
        traceback: Union[TracebackType, None],
    ) -> None:
        if exc_type is None:
            self.db.conn.commit()
        else:
            self.db.conn.rollback()


def __instantiate():
    """Raises a typing error if the driver has missing methods.

    Remove after class is finished.
    """
    MySqlDriver()
