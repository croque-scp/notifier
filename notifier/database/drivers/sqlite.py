import sqlite3
from typing import Dict, List, TypedDict

from notifier.database.drivers.base import DatabaseWithSqlFileCache
from notifier.types import (
    GlobalOverridesConfig,
    Subscription,
    SupportedSiteConfig,
    UserConfig,
)

sqlite3.enable_callback_tracebacks(True)


class SqliteDriver(DatabaseWithSqlFileCache):
    def __init__(self, location=":memory:"):
        self.conn = sqlite3.connect(location)
        self.conn.row_factory = sqlite3.Row
        self.clear_query_file_cache()
        self.execute_named("enable_foreign_keys")
        self.create_tables()

    def create_tables(self):
        self.execute_named("create_tables")

    def get_new_posts_for_user(
        self, user_id: str, search_timestamp: int
    ) -> TypedDict("NewPosts", {"thread_posts": List, "post_replies": List}):
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
