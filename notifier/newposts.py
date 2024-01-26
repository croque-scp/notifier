import logging
from operator import itemgetter
from typing import Iterator, List, Optional, TypedDict, cast

import feedparser

from notifier.config.user import parse_thread_url
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import RawPost, RawThreadMeta, ThreadInfo
from notifier.wikiconnection import Connection

logger = logging.getLogger(__name__)

# HTTPS for the RSS feed doesn't work for insecure wikis, but HTTP does
# work for secure wikis
new_posts_rss = "http://{}.wikidot.com/feed/forum/posts.xml"


def get_new_posts(
    database: BaseDatabaseDriver,
    connection: Connection,
    limit_wikis: Optional[List[str]] = None,
) -> None:
    """For each configured wiki, retrieve and store new posts.

    Returns tuple of counts of threads and posts downloaded.
    """
    wikis = database.get_supported_wikis()
    if limit_wikis is not None:
        wikis = [wiki for wiki in wikis if wiki["id"] in limit_wikis]

    logger.info("Downloading posts from wikis %s", wikis)
    for wiki in wikis:
        if limit_wikis is not None and wiki["id"] in limit_wikis:
            continue
        logger.info("Getting new posts %s", {"for wiki_id": wiki["id"]})
        try:
            fetch_posts_with_context(wiki["id"], database, connection)
        except Exception as error:
            logger.error(
                "Failed getting new posts %s",
                {"for wiki_id": wiki["id"], "reason": "unknown"},
                exc_info=error,
            )
            continue


def fetch_posts_with_context(
    wiki_id: str, database: BaseDatabaseDriver, connection: Connection
) -> None:
    """Look up new posts for a wiki and then attach their context. Stores
    the posts in the cache.
    """
    # Get the list of new posts from the forum's RSS
    new_posts = fetch_new_posts_rss(wiki_id)

    # Remove posts that are already recorded
    new_post_ids = database.find_new_posts(
        [new_post[1] for new_post in new_posts]
    )
    logger.debug(
        "Found posts in RSS %s",
        {
            "wiki_id": wiki_id,
            "full_post_count": len(new_posts),
            "new_post_count": len(new_post_ids),
        },
    )
    new_posts = [post for post in new_posts if post[1] in new_post_ids]

    # Find which of these posts were made in new threads
    new_thread_ids = database.find_new_threads(
        [new_post[0] for new_post in new_posts]
    )

    # Make a list of thread pages to iterate over
    # The post ID being None indicates that the full thread will be
    # iterated; otherwise, only the page that contains the specific post
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
    logger.debug(
        "Found new threads to download %s",
        {"wiki_id": wiki_id, "threads_count": len(threads_pages_to_get)},
    )
    for thread_id, post_id in threads_pages_to_get:
        if post_id is None and thread_id in full_threads_already_seen:
            # If a full thread is to be crawled (post_id is None) but it
            # has already been seen, skip it
            logger.debug(
                "Skipping download of thread %s",
                {
                    "wiki_id": wiki_id,
                    "thread_id": thread_id,
                    "reason": "thread already downloaded",
                },
            )
            continue
        if post_id is not None and post_id in posts_already_seen:
            # If a page is to be crawled (post_id is not None) but the post
            # has already been seen, we already have the page; skip it
            logger.debug(
                "Skipping download of post %s",
                {
                    "wiki_id": wiki_id,
                    "thread_id": thread_id,
                    "post_id": post_id,
                    "reason": "post already seen in downloaded thread",
                },
            )
            continue
        logger.debug(
            "Downloading thread%s %s",
            " containing post" if post_id is not None else "",
            {"wiki_id": wiki_id, "thread_id": thread_id, "post_id": post_id},
        )
        for post_index, thread_or_post in enumerate(
            connection.thread(wiki_id, thread_id, post_id)
        ):
            if post_index == 0:
                # First item is the thread meta info
                thread_meta = cast(RawThreadMeta, thread_or_post)
                thread_info: ThreadInfo = {
                    "id": thread_id,
                    "title": thread_meta["title"],
                    "wiki_id": wiki_id,
                    "category_id": thread_meta["category_id"],
                    "category_name": thread_meta["category_name"],
                    "creator_username": thread_meta["creator_username"],
                    "created_timestamp": thread_meta["created_timestamp"],
                }
                logger.debug("Storing metadata for thread %s", thread_info)
                database.store_thread(thread_info)
                continue
            # Remaining items are posts
            thread_post = cast(RawPost, thread_or_post)
            logger.debug(
                "Storing post %s",
                {
                    "wiki_id": wiki_id,
                    "post": thread_post,
                    "is first post": post_id is None and post_index == 1,
                },
            )
            database.store_post(thread_post)
            if post_id is None and post_index == 1:
                database.store_thread_first_post(thread_id, thread_post["id"])
            # Mark each post as seen
            posts_already_seen.append(thread_post["id"])
        if post_id is None:
            # If the full thread was crawled, mark it as seen
            full_threads_already_seen.append(thread_id)
        logger.debug(
            "Downloaded thread%s %s",
            " containing post" if post_id is not None else "",
            {
                "wiki_id": wiki_id,
                "thread_id": thread_id,
                "post_id": post_id,
                "cumulative_post_count": len(posts_already_seen),
                "cumulative_full_thread_count": len(full_threads_already_seen),
            },
        )


RssPost = TypedDict(
    "RssPost", {"thread_id": str, "post_id": str, "posted_timestamp": int}
)


def fetch_new_posts_rss(wiki_id: str) -> Iterator[RssPost]:
    """Get basic info about new posts from the wiki's RSS feed."""
    rss_url = new_posts_rss.format(wiki_id)
    try:
        feed = feedparser.parse(rss_url)
    except Exception as error:  # pylint: disable=broad-except
        logger.error(
            "Could not parse RSS feed %s", {"wiki_id": wiki_id}, exc_info=error
        )

    for entry in feed["entries"]:
        thread_id, post_id = itemgetter("thread_id", "post_id")(
            parse_thread_url(entry["id"])
        )
        yield {
            "thread_id": thread_id,
            "post_id": post_id,
            "posted_timestamp": int(entry["published_parsed"]),
        }
