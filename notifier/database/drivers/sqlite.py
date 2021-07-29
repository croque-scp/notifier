import json
import sqlite3
from sqlite3.dbapi2 import Cursor
from typing import Dict, Iterable

from notifier.database.drivers.base import DatabaseWithSqlFileCache
from notifier.types import (
    GlobalOverridesConfig,
    NewPostsInfo,
    Subscription,
    SupportedSiteConfig,
    UserConfig,
)

sqlite3.enable_callback_tracebacks(True)


class SqliteDriver(DatabaseWithSqlFileCache):
    """Database powered by SQLite."""

    def __init__(self, location=":memory:"):
        super().__init__(location)
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

    def store_global_overrides(
        self, global_overrides: GlobalOverridesConfig
    ) -> None:
        self.execute_named("drop_overrides")
        for wiki_id, overrides in global_overrides.item():
            self.execute_named(
                "store_global_override",
                {
                    "wiki_id": wiki_id,
                    "override_settings_json": json.dumps(overrides),
                },
            )
        self.conn.commit()

    def get_global_overrides(self) -> GlobalOverridesConfig:
        rows = self.execute_named("get_global_overrides").fetchall()
        overrides = {
            row["wiki_id"]: json.loads(row["override_settings_json"])
            for row in rows
        }
        return overrides

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

    def store_user_config(self, user_config: UserConfig):
        user_id = user_config.user_id
        # TODO
        self.conn.commit()

    def store_manual_sub(
        self, user_id: str, subscription: Subscription
    ) -> None:
        self.execute_named(
            "store_manual_sub",
            {
                "user_id": user_id,
                "thread_id": subscription["thread_id"],
                "post_id": subscription["post_id"],
                "sub": subscription["sub"],
            },
        )

    def store_supported_site(
        self, sites: Dict[str, SupportedSiteConfig]
    ) -> None:
        # Destroy all existing wikis in preparation for overwrite
        self.execute_named("remove_all_wikis")
        # Add each new wiki
        for wiki_id, wiki in sites.items():
            self.execute_named(
                "add_wiki",
                {"wiki_id": wiki_id, "wiki_secure": wiki["secure"]},
            )
            for alt in wiki["alts"]:
                self.execute_named(
                    "add_wiki_alias",
                    {"wiki_id": wiki_id, "alias": alt},
                )
        self.conn.commit()
