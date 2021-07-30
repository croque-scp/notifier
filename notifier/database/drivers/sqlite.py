import json
import sqlite3
from sqlite3.dbapi2 import Cursor
from typing import Iterable, List

from notifier.database.drivers.base import (
    BaseDatabaseDriver,
    DatabaseWithSqlFileCache,
)
from notifier.types import (
    GlobalOverridesConfig,
    NewPostsInfo,
    Subscription,
    SupportedWikiConfig,
    UserConfig,
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
        for wiki_id, overrides in global_overrides.item():
            self.execute_named(
                "store_global_override",
                {
                    "wiki_id": wiki_id,
                    "override_settings_json": json.dumps(overrides),
                },
            )
        self.conn.commit()

    def get_new_posts_for_user(
        self, user_id: str, search_timestamp: int
    ) -> NewPostsInfo:
        # Get new posts in subscribed threads
        thread_posts = self.execute_named(
            "get_posts_in_subscribed_threads",
            {"user_id": user_id, "search_timestamp": search_timestamp},
        ).fetchall()
        # Get new replies to subscribed posts
        post_replies = self.execute_named(
            "get_replies_to_subscribed_posts",
            {"user_id": user_id, "search_timestamp": search_timestamp},
        ).fetchall()
        # Remove duplicate posts - keep the ones that are post replies
        post_replies_ids = [post["id"] for post in post_replies]
        thread_posts = [
            thread_post
            for thread_post in thread_posts
            if thread_post["id"] not in post_replies_ids
        ]
        return {"thread_posts": thread_posts, "post_replies": post_replies}

    def store_user_configs(self, user_configs: List[UserConfig]) -> None:
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
                "post_id": subscription.get("post_id"),
                "sub": subscription["sub"],
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
                {"wiki_id": wiki["id"], "wiki_secure": wiki["secure"]},
            )
        self.conn.commit()
