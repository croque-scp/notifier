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
import time
from typing import List, Set, Tuple, cast
from uuid import uuid4

from notifier.config.user import fetch_user_configs, user_config_is_valid
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import LocalConfig, RawPost
from notifier.wikiconnection import Connection, ThreadNotExists

logger = logging.getLogger(__name__)

# A strict thread ID contains the ID of its wiki
StrictThreadId = Tuple[str, str]
# A strict post ID contains the IDs of its wiki and thread
StrictPostId = Tuple[str, str, str]


def clear_deleted_posts(
    frequency: str, database: BaseDatabaseDriver, connection: Connection
) -> None:
    """Remove deleted posts from the database.

    For each thread that a user on the given channel would soon be
    notified about, check that it still exists. If it does not, flag it as
    deleted in the cache, preventing it from emitting any notifications.

    If no users were about to be notified about a thread, there is no point
    bothering to look up whether it still exists or not.
    """
    logger.info(
        "Checking for deleted posts to clear %s", {"channel": frequency}
    )
    posts = find_posts_to_check(frequency, database)
    logger.info(
        "Found posts to check %s",
        {
            "post_count": len(posts),
            "thread_count": len(set(post[1] for post in posts)),
        },
    )
    deleted_threads, deleted_posts = delete_posts(posts, database, connection)
    logger.info(
        "Deleted threads %s",
        {
            "thread_count": len(deleted_threads),
            "wiki_count": len(set(d[0] for d in deleted_threads)),
        },
    )
    logger.info(
        "Deleted posts %s",
        {
            "post_count": len(deleted_posts),
            "thread_count": len(set(d[1] for d in deleted_posts)),
            "wiki_count": len(set(d[0] for d in deleted_posts)),
        },
    )


def find_posts_to_check(
    frequency: str, database: BaseDatabaseDriver
) -> Set[StrictPostId]:
    """For users on the given channel, find which threads and posts should
    be checked for deletion."""
    now = int(time.time())
    users = database.get_user_configs(frequency)
    posts_to_check: Set[StrictPostId] = set()
    for user in users:
        posts = database.get_notifiable_posts_for_user(
            user["user_id"], (user["last_notified_timestamp"] + 1, now)
        )
        for post in posts:
            posts_to_check.add(
                (post["wiki_id"], post["thread_id"], post["id"])
            )
    return posts_to_check


def delete_posts(
    posts: Set[StrictPostId],
    database: BaseDatabaseDriver,
    connection: Connection,
) -> Tuple[Set[StrictThreadId], Set[StrictPostId]]:
    """For each post, check if it exists. If it doesn't (or if the thread
    doesn't), mark it as deleted in the database."""
    deleted_threads: Set[StrictThreadId] = set()
    deleted_posts: Set[StrictPostId] = set()
    existing_posts: Set[str] = set()

    for wiki_id, thread_id, post_id in posts:
        if post_id in existing_posts:
            continue

        try:
            _, thread_posts = connection.thread(wiki_id, thread_id, post_id)
        except ThreadNotExists:
            raise NotImplementedError  # TODO Reimplement deletion

        # If there are no posts it means the targeted page doesn't exist and therefore neither does the targeted post
        if len(thread_posts) == 0:
            raise NotImplementedError  # TODO Reimplement deletion

        # If the post does exist, record all post IDs seen in that page, which are known to exist so don't need to be checked later
        existing_posts.update(post["id"] for post in thread_posts)

    return deleted_threads, deleted_posts


def rename_invalid_user_config_pages(
    local_config: LocalConfig, connection: Connection
) -> None:
    """Prepares invalid user config pages for deletion."""
    logger.info("Finding invalid user configs to prepare for deletion")
    # Get all user configs and filter out any that are valid
    invalid_configs = [
        (slug, config)
        for slug, config in fetch_user_configs(local_config, connection)
        if not user_config_is_valid(slug, config)
    ]
    logger.debug(
        "Found invalid configs to rename %s", {"count": len(invalid_configs)}
    )
    for slug, config in invalid_configs:
        try:
            connection.rename_page(
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
    local_config: LocalConfig, connection: Connection
) -> None:
    """Deletes prepared invalid user config pages."""
    logger.info("Finding pages marked for deletion")
    pages_to_delete = connection.listpages(
        local_config["config_wiki"],
        category="deleted",
        module_body="%%fullname%%",
    )
    for page in pages_to_delete:
        slug = page.get_text()
        try:
            connection.delete_page(local_config["config_wiki"], slug)
        except Exception as error:
            logger.error(
                "Couldn't delete page %s",
                {"slug": slug},
                exc_info=error,
            )
            continue
