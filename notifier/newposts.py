from functools import partial
from typing import List, Tuple, cast

import feedparser

from notifier.config.user import parse_thread_url
from notifier.database.drivers.base import BaseDatabaseDriver, try_cache
from notifier.wikiconnection import Connection

not_yet_checked = object()

# HTTPS for the RSS feed doesn't work for insecure wikis, but HTTP does
# work for secure wikis
new_posts_rss = "http://{}.wikidot.com/feed/forum/posts.xml"

rss_timestamp_format = "%a, %d %b %Y %X %z"


def get_new_posts(database: BaseDatabaseDriver, connection: Connection):
    """For each configured wiki, retrieve and store new posts."""
    for wiki in database.get_supported_wikis():
        print(f"Getting new posts for {wiki['id']}")
        try_cache(
            # TODO Probably need to make this lambda a def in order to do
            # and then context for each wiki
            get=partial(fetch_new_posts_rss, wiki["id"]),
            store=lambda: None,
            do_not_store=[],
        )


def fetch_posts_with_context(wiki_id: str, database: BaseDatabaseDriver):
    """Look up new posts for a wiki and then attach their context."""
    # Get the list of new posts from the forum's RSS
    new_posts = fetch_new_posts_rss(wiki_id)
    # Find which of these posts were made in new threads
    new_threads = database.find_new_threads(
        [new_post[0] for new_post in new_posts]
    )


def fetch_post_context(connection: Connection, wiki_id: str, thread_id: str):
    """Lookup the context of a post in its Wikidot thread.

    Bind the target post's parent post ID, if any, and then return the list
    of raw post information for all posts in the context.
    """
    connection.paginated_module(
        wiki_id,
        "forum/ForumViewThreadModule",
        index_key="pageNo",
        starting_index=1,
        t=thread_id.lstrip("t-"),
    )


def fetch_new_posts_rss(wiki_id: str) -> List[Tuple[int, int]]:
    """Get new posts from the wiki's RSS feed, returning only their thread
    and post IDs."""
    rss_url = new_posts_rss.format(wiki_id)
    try:
        feed = feedparser.parse(rss_url)
    except Exception:  # pylint: disable=broad-except
        # Will explore what errors this can throw later
        print("Caught exception when trying to parse feed", Exception)
    return [
        # Assert that the post ID is present
        cast(Tuple[int, int], parse_thread_url(entry["id"]))
        for entry in feed["entries"]
    ]
