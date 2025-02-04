import logging
from operator import itemgetter
from typing import Iterator, List, Optional, Set, TypedDict
import time

import feedparser

from notifier.config.user import parse_thread_url
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import RawPost, RawThreadMeta
from notifier.wikidot import Wikidot

logger = logging.getLogger(__name__)

# HTTPS for the RSS feed doesn't work for insecure wikis, but HTTP does
# work for secure wikis
new_posts_rss = "http://{}.wikidot.com/feed/forum/posts.xml"


def get_new_posts(
    database: BaseDatabaseDriver,
    wikidot: Wikidot,
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
            fetch_posts_with_context(wiki["id"], database, wikidot)
        except Exception as error:
            logger.error(
                "Failed getting new posts %s",
                {"for wiki_id": wiki["id"], "reason": "unknown"},
                exc_info=error,
            )
            continue


def fetch_posts_with_context(
    wiki_id: str, database: BaseDatabaseDriver, wikidot: Wikidot
) -> None:
    """Look up new posts for a wiki and then attach their context. Stores
    the posts in the cache.
    """
    # Get the list of new posts from the forum's RSS
    all_new_posts = list(fetch_new_posts_rss(wiki_id))

    # Filter out posts older than this run
    latest_post_timestamp = database.get_latest_post_timestamp(wiki_id)
    new_posts = sorted(
        [
            post
            for post in all_new_posts
            if post["posted_timestamp"] > latest_post_timestamp
        ],
        key=lambda p: (p["thread_id"], p["posted_timestamp"]),
    )

    logger.debug(
        "Found posts in RSS %s",
        {
            "wiki_id": wiki_id,
            "new_post_count": len(new_posts),
            "posts_in_rss": len(all_new_posts),
        },
    )

    # If there's at least one post, store the new highest timestamp for this wiki
    if len(new_posts) > 0:
        database.store_latest_post_timestamp(
            wiki_id, max(post["posted_timestamp"] for post in new_posts)
        )

    # Cache the latest downloaded thread to prevent multiple identical downloads when multiple posts share a thread
    thread_meta: RawThreadMeta = None  # type:ignore
    thread_page_posts: List[RawPost] = []

    # Track which context threads have been downloaded so that they won't be redownloaded this run
    context_threads_this_run: Set[str] = set()

    for new_post in new_posts:
        thread_id = new_post["thread_id"]
        post_id = new_post["post_id"]

        # Download the thread page only if it's not already cached
        post = next(
            (
                page_post
                for page_post in thread_page_posts
                if page_post["id"] == post_id
            ),
            None,
        )
        if post is None:
            logger.debug(
                "Downloading thread page containing post %s",
                {
                    "wiki_id": wiki_id,
                    "thread_id": thread_id,
                    "post_id": post_id,
                },
            )
            thread_meta, thread_page_posts = wikidot.thread(
                wiki_id, thread_id, post_id
            )
            post = next(
                (
                    page_post
                    for page_post in thread_page_posts
                    if page_post["id"] == post_id
                ),
                None,
            )
        if post is None:
            logger.error(
                "Requested post missing from downloaded thread %s",
                {
                    "wiki_id": wiki_id,
                    "thread_id": thread_id,
                    "post_id": post_id,
                },
            )
            raise RuntimeError("Requested post missing from downloaded thread")

        # For each kind of context, check if we already have it, and if not, fetch it

        # Context: wiki
        # The context wiki table is running double duty as the list of configured wikis, so we already have that context

        # Context: category
        if (
            thread_meta["category_id"] is not None
            and thread_meta["category_name"] is not None
        ):
            database.store_context_forum_category(
                {
                    "category_id": thread_meta["category_id"],
                    "category_name": thread_meta["category_name"],
                }
            )

        # Context: thread
        if thread_id not in context_threads_this_run:
            if thread_meta["current_page"] == 1:
                thread_first_post: RawPost = thread_page_posts[0]
                if thread_first_post["id"] == post_id:
                    # Special case where the searched post is the first post in the thread. E.g.:
                    #   - The user is subscribed to a thread that exists but has no posts yet
                    #   - The user is subscribed to a thread that doesn't exist but will
                    #   - The user is subscribed to new thread creation (a feature that doesn't exist yet but might someday)
                    # Currently this special case is not handled - the notification will have duplicated info
                    pass
            else:
                logger.debug(
                    "Downloading first thread page %s",
                    {"wiki_id": wiki_id, "thread_id": thread_id},
                )
                thread_first_post = wikidot.thread(wiki_id, thread_id)[1][0]
            database.store_context_thread(
                {
                    "thread_id": thread_id,
                    "thread_created_timestamp": thread_meta[
                        "created_timestamp"
                    ],
                    "thread_title": thread_meta["title"],
                    "thread_snippet": thread_first_post["snippet"],
                    "thread_creator_username": thread_meta["creator_username"],
                    "first_post_id": thread_first_post["id"],
                    "first_post_author_user_id": thread_first_post["user_id"],
                    "first_post_author_username": thread_first_post[
                        "username"
                    ],
                    "first_post_created_timestamp": thread_first_post[
                        "posted_timestamp"
                    ],
                }
            )
            context_threads_this_run.add(thread_id)

        # Context: parent post
        parent_post = next(
            (
                page_post
                for page_post in thread_page_posts
                if page_post["id"] == post["parent_post_id"]
            ),
            None,
        )
        if parent_post is not None:
            database.store_context_parent_post(
                {
                    "post_id": parent_post["id"],
                    "posted_timestamp": parent_post["posted_timestamp"],
                    "post_title": parent_post["title"],
                    "post_snippet": parent_post["snippet"],
                    "author_user_id": parent_post["user_id"],
                    "author_username": parent_post["username"],
                }
            )

        # Context complete
        # Now store the post itself
        logger.debug("Storing post %s", {"wiki_id": wiki_id, "post": post})
        database.store_post(
            {
                "post_id": post["id"],
                "posted_timestamp": post["posted_timestamp"],
                "post_title": post["title"],
                "post_snippet": post["snippet"],
                "author_user_id": post["user_id"],
                "author_username": post["username"],
                "context_wiki_id": wiki_id,
                "context_forum_category_id": thread_meta["category_id"],
                "context_thread_id": thread_id,
                "context_parent_post_id": post["parent_post_id"],
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
            "posted_timestamp": int(time.mktime(entry["published_parsed"])),
        }
