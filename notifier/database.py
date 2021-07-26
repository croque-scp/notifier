import sqlite3
from abc import ABC

from notifier.config.tool import SupportedSiteConfig

from .databasequeries import queries

sqlite3.enable_callback_tracebacks(True)


class BaseDatabaseDriver(ABC):
    pass


class SqliteDriver(BaseDatabaseDriver):
    def __init__(self, location=":memory:"):
        self.conn = sqlite3.connect(location)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(queries["enable_foreign_keys"])
        self.create_tables()

    def create_tables(self):
        self.conn.executescript(queries["create_tables_script"])

    def get_new_posts_for_user(self, user_id, search_timestamp):
        """Get new posts for the users with the given ID made since the
        given timestamp.

        Returns a dict containing the thread posts and the post replies.
        """
        # Get new posts in subscribed threads
        thread_posts = self.conn.execute(
            queries["get_posts_in_subscribed_threads"],
            {"user_id": user_id, "search_timestamp": search_timestamp},
        ).fetchall()
        # Get new replies to subscribed posts
        post_replies = self.conn.execute(
            queries["get_replies_to_subscribed_posts"],
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

    def store_supported_site(self, sites: dict[str, SupportedSiteConfig]):
        """Stores a set of supported sites in the database, overwriting any
        that are already present."""
        # Destroy all existing wikis in preparation for overwrite
        self.conn.executescript(queries["remove_all_wikis_script"])
        # Add each new wiki
        for wiki_id, wiki in sites.items():
            self.conn.execute(
                queries["add_wiki"],
                {"wiki_id": wiki_id, "wiki_secure": wiki["secure"]},
            )
            for alt in wiki["alts"]:
                self.conn.execute(
                    queries["add_wiki_alias"],
                    {"wiki_id": wiki_id, "alias": alt},
                )
        self.conn.commit()


DatabaseDriver = SqliteDriver
