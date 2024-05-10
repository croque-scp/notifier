"""Handles deletions.

Handles deletions of posts and threads from the database that appear to
have been deleted on the remote (but actually just flags them to be
ignored).

Also handles the purging of invalid user config pages from the
configuration wiki. An invalid user config page is any page where the slug
does not match the user who created it. This indicates that the page has
not been properly created, and may even be indicative of malicious intent.
In lieu of manual moderation these pages should be cleared.
"""

import logging
from datetime import datetime
from typing import List, Set, Tuple

from uuid import uuid4

from notifier.config.user import fetch_user_configs, user_config_is_valid
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier import timing
from notifier.types import LocalConfig, PostMeta
from notifier.wikidot import Wikidot, ThreadNotExists

logger = logging.getLogger(__name__)

# A strict thread ID contains the ID of its wiki
StrictThreadId = Tuple[str, str]
# A strict post ID contains the IDs of its wiki and thread
StrictPostId = Tuple[str, str, str]


def clear_deleted_posts(
    database: BaseDatabaseDriver, wikidot: Wikidot
) -> None:
    """Check for posts that have been deleted on the remote and delete them here too.

    It'd be inefficient to check every post for deletion all the time, but also it's important to make sure that all posts are checked frequently because they could be deleted at any point.

    Deletion checking works by dragging several consistently-spaced hour-long 'rakes' across the timeline, checking all selected posts for deletion. The rakes become more spread apart the further back in time they are, so posts are checked gradually less and less frequently. At a certain point checking for deletion no longer matters because the post will be cleared from the database anyway.
    """

    logger.info("Checking for deleted posts to clear")

    now_hour = timing.now.replace(minute=0, second=0, microsecond=0)
    now_hour_ts = int(datetime.timestamp(now_hour))

    posts = database.get_posts_to_check_for_deletion(now_hour_ts)
    delete_posts(posts, database, wikidot)


def delete_posts(
    posts: List[PostMeta],
    database: BaseDatabaseDriver,
    wikidot: Wikidot,
) -> None:
    """Sync post deletion states.

    For each post, check if it exists on the remote. If it doesn't (or if the thread doesn't), mark it as deleted in the database.
    """
    logger.debug("Checking posts for deletion %s", {"post_count": len(posts)})
    posts_ids = {p["post_id"] for p in posts}

    deleted_threads_ids: Set[str] = set()
    existing_posts_ids: Set[str] = set()
    deleted_posts_count = 0

    for post in posts:
        # A post that was already encountered is known to exist
        if post["post_id"] in existing_posts_ids:
            continue

        # A post in a thread that was already deleted is known not to exist and will already be deleted from the database
        if post["thread_id"] in deleted_threads_ids:
            continue

        try:
            # Throws ThreadNotExists if the thread doesn't exist
            thread_meta, thread_posts = wikidot.thread(
                post["wiki_id"], post["thread_id"], post["post_id"]
            )

            # If there are no posts it means the thread is empty - consider it deleted
            # (This is only true when targeting a specific post - if we were targeting a page number, no posts would mean that there are not that many pages)
            if len(thread_posts) == 0:
                raise ThreadNotExists
        except ThreadNotExists:
            logger.debug(
                "Deleting thread context %s",
                {"wiki_id": post["wiki_id"], "thread_id": post["thread_id"]},
            )
            database.delete_context_thread(post["thread_id"])
            deleted_threads_ids.add(post["thread_id"])
            continue

        # The thread exists - might as well keep the context up to date while we're here
        if thread_meta["current_page"] == 1:
            # This won't happen more than once because other posts in page 1 will be marked as existing
            logger.debug(
                "Updating thread context %s",
                {"wiki_id": post["wiki_id"], "thread_id": post["thread_id"]},
            )
            thread_first_post = thread_posts[0]
            database.store_context_thread(
                {
                    "thread_id": post["thread_id"],
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

        thread_posts_ids = {tp["id"] for tp in thread_posts}

        # Record all post IDs seen in the page, which are known to exist so don't need to be checked later
        existing_posts_ids.update(thread_posts_ids & posts_ids)

        # Delete the post if it's not in the thread page
        if post["post_id"] not in thread_posts_ids:
            logger.debug("Deleting post %s", post)
            database.delete_post(post["post_id"])
            deleted_posts_count += 1
            continue

        # If there are more posts in the queue to be checked that a) have been deleted and b) would have been on this page, the page will unfortunately need to be redownloaded again for each, as there's no way to know from here that we can mark them as deleted

    logger.debug(
        "Finished deleting posts %s",
        {"deleted_posts_count": deleted_posts_count},
    )


def rename_invalid_user_config_pages(
    local_config: LocalConfig, wikidot: Wikidot
) -> None:
    """Prepares invalid user config pages for deletion."""
    logger.info("Finding invalid user configs to prepare for deletion")
    # Get all user configs and filter out any that are valid
    invalid_configs = [
        (slug, config)
        for slug, config in fetch_user_configs(local_config, wikidot)
        if not user_config_is_valid(slug, config)
    ]
    logger.debug(
        "Found invalid configs to rename %s", {"count": len(invalid_configs)}
    )
    for slug, config in invalid_configs:
        try:
            wikidot.rename_page(
                local_config["config_wiki"], slug, f"deleted:{uuid4()}"
            )
        except Exception as error:
            logger.error(
                "Couldn't rename config page %s",
                {"slug": slug},
                exc_info=error,
            )
            continue


def delete_prepared_invalid_user_pages(
    local_config: LocalConfig, wikidot: Wikidot
) -> None:
    """Deletes prepared invalid user config pages."""
    logger.info("Finding pages marked for deletion")
    pages_to_delete = wikidot.listpages(
        local_config["config_wiki"],
        category="deleted",
        module_body="%%fullname%%",
    )
    for page in pages_to_delete:
        slug = page.get_text()
        try:
            wikidot.delete_page(local_config["config_wiki"], slug)
        except Exception as error:
            logger.error(
                "Couldn't delete page %s",
                {"slug": slug},
                exc_info=error,
            )
            continue
