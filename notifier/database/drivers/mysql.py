import json
import logging
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, Tuple, cast

import pymysql
from pymysql.constants.CLIENT import MULTI_STATEMENTS
from pymysql.cursors import DictCursor

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.utils import BaseDatabaseWithSqlFileCache
from notifier.types import (
    CachedUserConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
    PostReplyInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
    ThreadPostInfo,
)

logger = logging.getLogger(__name__)


class MySqlDriver(BaseDatabaseDriver, BaseDatabaseWithSqlFileCache):
    """Database powered by MySQL."""

    def __init__(
        self, database_name: str, *, host: str, username: str, password: str
    ):

        BaseDatabaseDriver.__init__(self, database_name)
        BaseDatabaseWithSqlFileCache.__init__(self)

        logger.info("Connecting to database...")
        self.conn = pymysql.connect(
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
        params: Iterable = None,
        cursor: DictCursor = None,
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

    def scrub_database(self, database_name: str):
        if not database_name.endswith("_test"):
            raise RuntimeError("Don't scrub the production database")
        with self.transaction() as cursor:
            self.execute_named("_scrub", {"db_name": database_name}, cursor)
            scrubs = [row["scrub"] for row in cursor.fetchall()]
            for scrub in scrubs:
                cursor.execute(scrub)
        logger.info("Dropped tables %s", {"count": len(scrubs)})
        self.create_tables()

    def apply_migrations(self) -> None:
        migration_version = int(
            (
                self.execute_named("get_migration_version").fetchone()
                or {"version": -1}
            )["version"]
        )
        # If there is no version set, use the create_tables procedure as a
        # shortcut to the most recent migration
        if migration_version == -1:
            self.create_tables()
            return
        # Filter out migrations that have already been applied
        migrations = [
            (version, migration)
            for version, migration in sorted(self.get_migrations().items())
            if version > migration_version
        ]
        for version, migration in migrations:
            logger.info(
                "Applying migration %s",
                {"from version": migration_version, "to version": version},
            )
            with self.transaction() as cursor:
                cursor.execute(migration)
                migration_version = version

    def create_tables(self):
        with self.transaction() as cursor:
            self.execute_named("create_tables", None, cursor)

    def get_global_overrides(self) -> GlobalOverridesConfig:
        rows = self.execute_named("get_global_overrides").fetchall()
        overrides = {
            row["wiki_id"]: json.loads(row["override_settings_json"])
            for row in rows
        }
        return overrides

    def store_global_overrides(
        self, global_overrides: GlobalOverridesConfig
    ) -> None:
        # Overwrite all current overrides
        with self.transaction() as cursor:
            self.execute_named("delete_overrides", None, cursor)
            for wiki_id, overrides in global_overrides.items():
                overrides_json = json.dumps(overrides)
                # DB limits this field to 2000 characters
                if len(overrides_json) > 1500:
                    logger.warning(
                        "Override string length near limit %s",
                        {"wiki_id": wiki_id, "length": len(overrides_json)},
                    )
                if len(overrides_json) > 2000:
                    logger.warning(
                        "Override string length above limit %s",
                        {"wiki_id": wiki_id, "length": len(overrides_json)},
                    )
                    continue
                self.execute_named(
                    "store_global_override",
                    {
                        "wiki_id": wiki_id,
                        "override_settings_json": json.dumps(overrides),
                    },
                    cursor,
                )

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
            # The last notified timestamp can be NULL (originating from the
            # LEFT JOIN) if the user has never been notified and thus does
            # not have an entry in the user_last_notified table
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
                for row in self.execute_named(
                    "get_auto_sub_posts_for_user",
                    {"user_id": user_config["user_id"]},
                ).fetchall()
                + self.execute_named(
                    "get_auto_sub_threads_for_user",
                    {"user_id": user_config["user_id"]},
                ).fetchall()
            ]
        return user_configs

    def store_user_configs(self, user_configs: List[RawUserConfig]) -> None:
        with self.transaction() as cursor:
            # Overwrite all current configs
            self.execute_named("delete_user_configs", None, cursor)
            for user_config in user_configs:
                self.execute_named(
                    "store_user_config",
                    {
                        "user_id": user_config["user_id"],
                        "username": user_config["username"],
                        "frequency": user_config["frequency"],
                        "language": user_config["language"],
                        "delivery": user_config["delivery"],
                    },
                    cursor,
                )
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
                self.execute_named(
                    "store_new_user_last_notified",
                    {
                        "user_id": user_config["user_id"],
                        "notified_timestamp": user_config[
                            "user_base_notified"
                        ],
                    },
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

    def store_thread(
        self,
        wiki_id: str,
        category: Tuple[Optional[str], Optional[str]],
        thread: Tuple[str, str, Optional[str], int],
    ) -> None:
        thread_id, thread_title, creator_username, created_timestamp = thread
        category_id, category_name = category
        if category_id is not None and category_name is not None:
            self.execute_named(
                "store_category", {"id": category_id, "name": category_name}
            )
        self.execute_named(
            "store_thread",
            {
                "id": thread_id,
                "title": thread_title,
                "wiki_id": wiki_id,
                "category_id": category_id,
                "creator_username": creator_username,
                "created_timestamp": created_timestamp,
            },
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


def __instantiate():
    """Raises a typing error if the driver has missing methods."""
    MySqlDriver("", host="", username="", password="")
