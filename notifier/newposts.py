from typing import List, Tuple, cast

import feedparser

from notifier.config.user import parse_thread_url
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import RawPost, RawThreadMeta
from notifier.wikiconnection import Connection

# HTTPS for the RSS feed doesn't work for insecure wikis, but HTTP does
# work for secure wikis
new_posts_rss = "http://{}.wikidot.com/feed/forum/posts.xml"


def get_new_posts(database: BaseDatabaseDriver, connection: Connection):
    """For each configured wiki, retrieve and store new posts."""
    for wiki in database.get_supported_wikis():
        print(f"Getting new posts for {wiki['id']}")
        fetch_posts_with_context(wiki["id"], database, connection)


def fetch_posts_with_context(
    wiki_id: str, database: BaseDatabaseDriver, connection: Connection
):
    """Look up new posts for a wiki and then attach their context. Stores
    the posts in the cache."""
    # Get the list of new posts from the forum's RSS
    new_posts = fetch_new_posts_rss(wiki_id)
    # Find which of these posts were made in new threads
    new_thread_ids = database.find_new_threads(
        [new_post[0] for new_post in new_posts]
    )
    # Make a list of thread pages to iterate over
    # The post ID being None indicates that the full thread will be
    # iterated; otherwise, only the page that contains the specific post is
    # will be iterated
    threads_pages_to_get = [
        (thread_id, None if thread_id in new_thread_ids else post_id)
        for thread_id, post_id in new_posts
    ]
    # Sort the list so that full threads will be crawled first, followed by
    # individual pages - this is to optimise deduplication
    threads_pages_to_get.sort(key=lambda page: page[1] is not None)
    # Record posts and full threads that have already been seen to as not
    # to duplicate any API calls
    posts_already_seen: List[str] = []
    full_threads_already_seen: List[str] = []
    # Download each of the new threads
    for thread_id, post_id in threads_pages_to_get:
        if post_id is None and thread_id in full_threads_already_seen:
            # If a full thread is to be crawled (post_id is None) but it
            # has already been seen, skip it
            continue
        if post_id is not None and post_id in posts_already_seen:
            # If a page is to be crawled (post_id is not None) but the post
            # has already been seen, we already have the page; skip it
            continue
        for post_index, thread_or_post in enumerate(
            connection.thread(wiki_id, thread_id, post_id)
        ):
            if post_index == 0:
                # First 'post' is the thread meta info
                thread_meta = cast(RawThreadMeta, thread_or_post)
                database.store_thread(
                    wiki_id,
                    (thread_meta["category_id"], thread_meta["category_name"]),
                    (
                        thread_id,
                        thread_meta["title"],
                        thread_meta["creator_username"],
                        thread_meta["created_timestamp"],
                    ),
                )
                continue
            # Remaining posts are actually posts
            post = cast(RawPost, thread_or_post)
            database.store_post(post)
            # Mark each post as seen
            posts_already_seen.append(post["id"])
        if post_id is None:
            # If the full thread was crawled, mark it as seen
            full_threads_already_seen.append(thread_id)


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


def fetch_new_posts_rss(wiki_id: str) -> List[Tuple[str, str]]:
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
        cast(Tuple[str, str], parse_thread_url(entry["id"]))
        for entry in feed["entries"]
    ]
