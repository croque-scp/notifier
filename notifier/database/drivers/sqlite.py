import json
import sqlite3
from sqlite3.dbapi2 import Cursor
from typing import Iterable, List, Tuple, cast

from notifier.database.drivers.base import (
    BaseDatabaseDriver,
    DatabaseWithSqlFileCache,
)
from notifier.types import (
    CachedUserConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
)

sqlite3.enable_callback_tracebacks(True)


class SqliteDriver(DatabaseWithSqlFileCache, BaseDatabaseDriver):
    """Database powered by SQLite."""

    def __init__(self, location=":memory:"):
        super().__init__()
        self.conn = sqlite3.connect(location)
        self.conn.row_factory = sqlite3.Row
        self.execute_named("enable_foreign_keys")
        self.create_tables()

    def execute_named(
        self, query_name: str, params: Iterable = None
    ) -> Cursor:
        """Execute a named query against the database. The query is read
        either from file or the cache.

        :param query_name: The name of the query to execute, which must
        have a corresponding SQL file.
        :param params: SQL parameters to pass to the query.
        :returns: The resultant cursor of the query.
        """
        self.cache_named_query(query_name)
        query = self.query_cache[query_name]["query"]
        if self.query_cache[query_name]["script"]:
            if params is not None:
                raise ValueError("Script does not accept params")
            return self.conn.executescript(query)
        if params is None:
            params = {}
        return self.conn.execute(query, params)

    def create_tables(self):
        self.execute_named("create_tables")

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
        self.execute_named("delete_overrides")
        for wiki_id, overrides in global_overrides.items():
            self.execute_named(
                "store_global_override",
                {
                    "wiki_id": wiki_id,
                    "override_settings_json": json.dumps(overrides),
                },
            )
        self.conn.commit()

    def find_new_threads(self, thread_ids: Iterable[str]) -> List[str]:
        return [
            thread_id
            for thread_id in thread_ids
            if not bool(
                self.execute_named(
                    "check_thread_exists", {"id": thread_id}
                ).fetchone()[0]
            )
        ]

    def get_new_posts_for_user(
        self, user_id: str, timestamp_range: Tuple[int, int]
    ) -> NewPostsInfo:
        lower_timestamp, upper_timestamp = timestamp_range
        criterion = {
            "user_id": user_id,
            "upper_timestamp": upper_timestamp,
            "lower_timestamp": lower_timestamp,
        }
        thread_posts = self.execute_named(
            "get_posts_in_subscribed_threads", criterion
        ).fetchall()
        post_replies = self.execute_named(
            "get_replies_to_subscribed_posts", criterion
        ).fetchall()
        # Remove duplicate posts - keep the ones that are post replies
        post_replies_ids = [post["id"] for post in post_replies]
        thread_posts = [
            thread_post
            for thread_post in thread_posts
            if thread_post["id"] not in post_replies_ids
        ]
        return {"thread_posts": thread_posts, "post_replies": post_replies}

    def get_user_configs(self, frequency: str) -> List[CachedUserConfig]:
        return [
            cast(CachedUserConfig, dict(row))
            for row in self.execute_named(
                "get_user_configs_from_frequency", {"frequency": frequency}
            ).fetchall()
        ]

    def store_user_configs(self, user_configs: List[RawUserConfig]) -> None:
        # Overwrite all current configs
        self.execute_named("delete_user_configs")
        self.execute_named("delete_manual_subs")
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
            )
            for subscription in (
                user_config["subscriptions"] + user_config["unsubscriptions"]
            ):
                self.store_manual_sub(user_config["user_id"], subscription)
        self.conn.commit()

    def store_manual_sub(
        self, user_id: str, subscription: Subscription
    ) -> None:
        self.execute_named(
            "store_manual_sub",
            {
                "user_id": user_id,
                "thread_id": subscription["thread_id"],
                # "post_id": subscription.get("post_id"),
                "post_id": subscription["post_id"],
                "sub": subscription["sub"],
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
        return wikis

    def store_supported_wikis(self, wikis: List[SupportedWikiConfig]) -> None:
        # Destroy all existing wikis in preparation for overwrite
        self.execute_named("delete_wikis")
        # Add each new wiki
        for wiki in wikis:
            self.execute_named(
                "add_wiki",
                {
                    "wiki_id": wiki["id"],
                    "wiki_name": wiki["name"],
                    "wiki_secure": wiki["secure"],
                },
            )
        self.conn.commit()

    def store_thread(
        self,
        wiki_id: str,
        category: Tuple[str, str],
        thread: Tuple[str, str],
    ) -> None:
        thread_id, thread_title = thread
        category_id, category_name = category
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
