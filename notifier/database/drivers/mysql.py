import logging
from contextlib import contextmanager
from itertools import chain
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, cast

import pymysql
from pymysql import Connection
from pymysql.constants.CLIENT import MULTI_STATEMENTS
from pymysql.cursors import DictCursor

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.utils import BaseDatabaseWithSqlFileCache
from notifier.types import (
    ActivationLogDump,
    CachedUserConfig,
    ChannelLogDump,
    LogDump,
    NewPostsInfo,
    PostReplyInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
    ThreadInfo,
    ThreadPostInfo,
)

logger = logging.getLogger(__name__)


class MySqlDriver(BaseDatabaseDriver, BaseDatabaseWithSqlFileCache):
    """Database powered by MySQL."""

    conn: "pymysql.Connection[DictCursor]"

    def __init__(
        self, database_name: str, *, host: str, username: str, password: str
    ):
        self.database_name = database_name

        BaseDatabaseDriver.__init__(self, database_name)
        BaseDatabaseWithSqlFileCache.__init__(self)

        logger.info("Connecting to database...")
        self.conn: "Connection[DictCursor]" = pymysql.connect(
            host=host,
            user=username,
            password=password,
            database=database_name,
            # Cursor is accessible like a dict (buffered)
            cursorclass=DictCursor,
            # Autocommit except during explicit transactions
            autocommit=True,
            # Enable 'executescript'-like functionality for all statements
            client_flag=MULTI_STATEMENTS,
        )
        logger.info("Connected to database")

        self.apply_migrations()

    def __del__(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator[DictCursor]:
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
        self,
        query_name: str,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[DictCursor] = None,
    ) -> DictCursor:
        """Execute a named query against the database. The query is read
        either from file or the cache.

        :param query_name: The name of the query to execute, which must
        have a corresponding SQL file.
        :param params: SQL parameters to pass to the query.
        :param cursor: A cursor to use for the query. If not specified, a
        new one will be created. The cursor will be returned.
        :returns: The resultant cursor of the query.
        """
        self.cache_named_query(query_name)
        query = self.query_cache[query_name]["query"]
        if cursor is None:
            cursor = self.conn.cursor()
        if self.query_cache[query_name]["script"] and params is not None:
            raise ValueError("Script does not accept params")
        cursor.execute(query, {} if params is None else params)
        return cursor

    def scrub_database(self) -> None:
        logger.info("Scrubbing database")
        if not self.database_name.endswith("_test"):
            raise RuntimeError("Don't scrub the production database")
        # To the scrub the database, we apply all down migrations and then
        # all up migrations
        try:
            current_version = int(
                (
                    self.execute_named("get_migration_version").fetchone()
                    or {"version": -1}
                )["version"]
            )
        except pymysql.err.ProgrammingError:
            logger.info("Nothing to scrub?")
            return
        for required_version, migration in reversed(
            list(enumerate(self.get_migrations("down")))
        ):
            if required_version > current_version:
                continue
            logger.info(
                "Applying migration %s",
                {
                    "from version": current_version,
                    "to version": required_version - 1,
                },
            )
            with self.transaction() as cursor:
                cursor.execute(migration)
                if required_version > 0:
                    self.execute_named(
                        "set_migration_version",
                        {"version": str(required_version).rjust(3, "0")},
                    )
                    current_version = required_version
        logger.info("Scrubbed database")

        self.apply_migrations()

    def apply_migrations(self) -> None:
        logger.info("Applying migrations...")
        try:
            current_version = int(
                (
                    self.execute_named("get_migration_version").fetchone()
                    or {"version": -1}
                )["version"]
            )
        except pymysql.err.ProgrammingError:
            # Raised when the meta table doesn't exist
            current_version = -1
        logger.debug("Database migration version is %s", current_version)
        for next_version, migration in enumerate(self.get_migrations("up")):
            if next_version <= current_version:
                continue
            logger.info(
                "Applying migration %s",
                {
                    "from version": current_version,
                    "to version": next_version,
                },
            )
            with self.transaction() as cursor:
                cursor.execute(migration)
                self.execute_named(
                    "set_migration_version",
                    {"version": str(next_version).rjust(3, "0")},
                )
            current_version = next_version
        logger.info("Applied migrations")

    def create_tables(self) -> None:
        with self.transaction() as cursor:
            self.execute_named("create_tables", None, cursor)

    def find_new_posts(self, post_ids: Iterable[str]) -> List[str]:
        return [
            post_id
            for post_id in post_ids
            if (
                row := self.execute_named(
                    "check_post_exists", {"id": post_id}
                ).fetchone()
            )
            is None
            or not row["post_exists"]
        ]

    def find_new_threads(self, thread_ids: Iterable[str]) -> List[str]:
        return [
            thread_id
            for thread_id in thread_ids
            if (
                row := self.execute_named(
                    "check_thread_exists", {"id": thread_id}
                ).fetchone()
            )
            is None
            or not row["thread_exists"]
        ]

    def mark_thread_as_deleted(self, thread_id: str) -> None:
        self.execute_named("mark_thread_as_deleted", {"id": thread_id})

    def mark_post_as_deleted(self, post_id: str) -> None:
        self.execute_named("mark_post_as_deleted", {"id": post_id})
        # Find any children of this post and delete them, too
        for child in self.execute_named(
            "get_post_children", {"id": post_id}
        ).fetchall():
            self.mark_post_as_deleted(child["id"])

    def get_new_posts_for_user(
        self, user_id: str, timestamp_range: Tuple[int, int]
    ) -> NewPostsInfo:
        lower_timestamp, upper_timestamp = timestamp_range
        criterion = {
            "user_id": user_id,
            "upper_timestamp": upper_timestamp,
            "lower_timestamp": lower_timestamp,
        }
        thread_posts = cast(
            List[ThreadPostInfo],
            list(
                self.execute_named(
                    "get_posts_in_subscribed_threads", criterion
                ).fetchall()
            ),
        )
        post_replies = cast(
            List[PostReplyInfo],
            list(
                self.execute_named(
                    "get_replies_to_subscribed_posts", criterion
                ).fetchall()
            ),
        )
        # Remove duplicate posts - keep the ones that are post replies
        post_replies_ids = [post["id"] for post in post_replies]
        thread_posts = [
            thread_post
            for thread_post in thread_posts
            if thread_post["id"] not in post_replies_ids
        ]
        return {"thread_posts": thread_posts, "post_replies": post_replies}

    def get_user_configs(self, frequency: str) -> List[CachedUserConfig]:
        user_configs = [
            cast(CachedUserConfig, dict(row))
            for row in self.execute_named(
                "get_user_configs_for_frequency", {"frequency": frequency}
            ).fetchall()
        ]
        for user_config in user_configs:
            # The last notified timestamp can be NULL if the user has never been notified
            if user_config["last_notified_timestamp"] is None:
                user_config["last_notified_timestamp"] = 0
            user_config["manual_subs"] = [
                cast(Subscription, dict(row))
                for row in self.execute_named(
                    "get_manual_subs_for_user",
                    {"user_id": user_config["user_id"]},
                ).fetchall()
            ]
            user_config["auto_subs"] = [
                cast(Subscription, dict(row))
                for row in chain(
                    self.execute_named(
                        "get_auto_sub_posts_for_user",
                        {"user_id": user_config["user_id"]},
                    ).fetchall(),
                    self.execute_named(
                        "get_auto_sub_threads_for_user",
                        {"user_id": user_config["user_id"]},
                    ).fetchall(),
                )
            ]
        return user_configs

    def count_user_configs(self) -> int:
        return cast(
            int,
            (
                self.execute_named("count_user_configs").fetchone()
                or {"count": 0}
            )["count"],
        )

    def get_notifiable_users(
        self, frequency: str, post_lower_timestamp_limit: int
    ) -> List[str]:
        logger.debug("Caching post context...")
        self.execute_named(
            "cache_post_context",
            {"post_lower_timestamp_limit": post_lower_timestamp_limit},
        )
        logger.debug("Retrieving notifiable users users...")
        user_ids = [
            cast(str, row["user_id"])
            for row in self.execute_named(
                "get_user_ids_for_frequency_with_notifications",
                {"frequency": frequency},
            ).fetchall()
        ]
        return user_ids

    def store_user_configs(
        self,
        user_configs: List[RawUserConfig],
        *,
        overwrite_existing: bool = True,
    ) -> None:
        # Delete stored user configs not in the incoming batch
        if overwrite_existing:
            with self.transaction() as cursor:
                stored_user_ids = [
                    cast(str, row["user_id"])
                    for row in self.execute_named(
                        "get_user_ids", None, cursor
                    ).fetchall()
                ]
                incoming_user_ids = [
                    user_config["user_id"] for user_config in user_configs
                ]
                for stored_user_id in stored_user_ids:
                    if stored_user_id not in incoming_user_ids:
                        logger.debug(
                            "Deleting user config not found in new data %s",
                            {"stored_user_id": stored_user_id},
                        )
                        self.execute_named(
                            "delete_user_config",
                            {"user_id": stored_user_id},
                            cursor,
                        )

        # Update stored user configs with new data
        with self.transaction() as cursor:
            for user_config in user_configs:
                self.execute_named(
                    "store_user_config",
                    {
                        "user_id": user_config["user_id"],
                        "username": user_config["username"],
                        "frequency": user_config["frequency"],
                        "language": user_config["language"],
                        "delivery": user_config["delivery"],
                        "tags": user_config["tags"],
                        "base_notified_timestamp_if_new_user": user_config[
                            "user_base_notified"
                        ],
                    },
                    cursor,
                )
                # Wipe all subscriptions in case any have been removed
                self.execute_named(
                    "delete_manual_subs_for_user",
                    {"user_id": user_config["user_id"]},
                    cursor,
                )
                # Add all new subscriptions from scratch
                for subscription in (
                    user_config["subscriptions"]
                    + user_config["unsubscriptions"]
                ):
                    self.execute_named(
                        "store_manual_sub",
                        {
                            "user_id": user_config["user_id"],
                            "thread_id": subscription["thread_id"],
                            "post_id": subscription.get("post_id"),
                            "sub": subscription["sub"],
                        },
                        cursor,
                    )

    def store_user_last_notified(
        self, user_id: str, last_notified_timestamp: int
    ) -> None:
        self.execute_named(
            "store_user_last_notified",
            {
                "user_id": user_id,
                "notified_timestamp": last_notified_timestamp,
            },
        )

    def get_supported_wikis(self) -> List[SupportedWikiConfig]:
        wikis = self.execute_named("get_supported_wikis").fetchall()
        return cast(List[SupportedWikiConfig], list(wikis))

    def count_supported_wikis(self) -> int:
        return cast(
            int,
            (
                self.execute_named("count_supported_wikis").fetchone()
                or {"count": 0}
            )["count"],
        )

    def store_supported_wikis(self, wikis: List[SupportedWikiConfig]) -> None:
        # Destroy all existing wikis in preparation for overwrite
        with self.transaction() as cursor:
            self.execute_named("delete_wikis", None, cursor)
            for wiki in wikis:
                self.execute_named(
                    "add_wiki",
                    {
                        "wiki_id": wiki["id"],
                        "wiki_name": wiki["name"],
                        "wiki_secure": wiki["secure"],
                    },
                    cursor,
                )

    def store_thread(self, thread: ThreadInfo) -> None:
        if (
            thread["category_id"] is not None
            and thread["category_name"] is not None
        ):
            self.execute_named(
                "store_category",
                {"id": thread["category_id"], "name": thread["category_name"]},
            )
        self.execute_named(
            "store_thread",
            {
                "id": thread["id"],
                "title": thread["title"],
                "wiki_id": thread["wiki_id"],
                "category_id": thread["category_id"],
                "creator_username": thread["creator_username"],
                "created_timestamp": thread["created_timestamp"],
            },
        )

    def store_thread_first_post(self, thread_id: str, post_id: str) -> None:
        self.execute_named(
            "store_thread_first_post",
            {"thread_id": thread_id, "post_id": post_id},
        )

    def store_post(self, post: RawPost) -> None:
        self.execute_named(
            "store_post",
            {
                "id": post["id"],
                "thread_id": post["thread_id"],
                "parent_post_id": post["parent_post_id"],
                "posted_timestamp": post["posted_timestamp"],
                "title": post["title"],
                "snippet": post["snippet"],
                "user_id": post["user_id"],
                "username": post["username"],
            },
        )

    def store_channel_log_dump(self, log: ChannelLogDump) -> None:
        """Store a channel log dump."""
        self.execute_named(
            "store_channel_log_dump",
            {
                "channel": log.get("channel", None),
                "start_timestamp": log.get("start_timestamp", None),
                "end_timestamp": log.get("end_timestamp", None),
                "notified_user_count": log.get("notified_user_count", None),
            },
        )

    def store_activation_log_dump(self, log: ActivationLogDump) -> None:
        """Store an activation log dump."""
        self.execute_named(
            "store_activation_log_dump",
            {
                "start_timestamp": log.get("start_timestamp", None),
                "config_start_timestamp": log.get(
                    "config_start_timestamp", None
                ),
                "config_end_timestamp": log.get("config_end_timestamp", None),
                "getpost_start_timestamp": log.get(
                    "getpost_start_timestamp", None
                ),
                "getpost_end_timestamp": log.get(
                    "getpost_end_timestamp", None
                ),
                "notify_start_timestamp": log.get(
                    "notify_start_timestamp", None
                ),
                "notify_end_timestamp": log.get("notify_end_timestamp", None),
                "end_timestamp": log.get("end_timestamp", None),
            },
        )

    def get_log_dumps_since(self, timestamp_range: Tuple[int, int]) -> LogDump:
        """Retrieve log dumps stored in the time range."""
        lower_timestamp, upper_timestamp = timestamp_range
        return {
            "activations": cast(
                List[ActivationLogDump],
                self.execute_named(
                    "get_activation_log_dumps",
                    {
                        "lower_timestamp": lower_timestamp,
                        "upper_timestamp": upper_timestamp,
                    },
                ).fetchall(),
            ),
            "channels": cast(
                List[ChannelLogDump],
                self.execute_named(
                    "get_channel_log_dumps",
                    {
                        "lower_timestamp": lower_timestamp,
                        "upper_timestamp": upper_timestamp,
                    },
                ).fetchall(),
            ),
        }


def __instantiate() -> None:
    """Raises a typing error if the driver has missing methods."""
    MySqlDriver("", host="", username="", password="")
