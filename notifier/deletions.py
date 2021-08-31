import time
from typing import List, Set, Tuple, cast

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import RawPost
from notifier.wikiconnection import Connection, ThreadNotExists

# A strict thread ID contains the ID of its wiki
StrictThreadId = Tuple[str, str]
# A strict post ID contains the IDs of its wiki and thread
StrictPostId = Tuple[str, str, str]


def clear_deleted_posts(
    frequency: str, database: BaseDatabaseDriver, connection: Connection
):
    """Remove deleted posts from the database.

    For each thread that a user on the given channel would soon be
    notified about, check that it still exists. If it does not, flag it as
    deleted in the cache, preventing it from emitting any notifications.

    If no users were about to be notified about a thread, there is no point
    bothering to look up whether it still exists or not.
    """
    print(f"Clearing deleted posts from the {frequency} channel")
    posts = find_posts_to_check(frequency, database)
    print(
        f"Found {len(posts)} posts to check"
        f" in {len(set(post[1] for post in posts))} threads"
    )
    deleted_threads, deleted_posts = delete_posts(posts, database, connection)
    print(
        f"Deleted {len(deleted_threads)} threads"
        f" in {len(set(d[0] for d in deleted_threads))} wikis"
    )
    print(
        f"Deleted {len(deleted_posts)} posts"
        f" in {len(set(d[1] for d in deleted_posts))} threads"
        f" in {len(set(d[0] for d in deleted_posts))} wikis"
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
        posts = database.get_new_posts_for_user(
            user["user_id"], (user["last_notified_timestamp"], now)
        )
        for post in posts["thread_posts"]:
            posts_to_check.add(
                (post["wiki_id"], post["thread_id"], post["id"])
            )
        for reply in posts["post_replies"]:
            posts_to_check.add(
                (reply["wiki_id"], reply["thread_id"], reply["id"])
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

        thread_info = connection.thread(wiki_id, thread_id, post_id)
        # The first iteration is a special case and returns information
        # about the thread; it will always succeed if the thread exists
        try:
            next(thread_info)
        except ThreadNotExists:
            database.mark_thread_as_deleted(thread_id)
            deleted_threads.add((wiki_id, thread_id))
            continue

        # Subsequent iterations return posts from the targeted page; if
        # there are no posts it means the targeted page doesn't exist and
        # therefore neither does the targeted post
        thread_posts = cast(List[RawPost], list(thread_info))
        if len(thread_posts) == 0:
            database.mark_post_as_deleted(post_id)
            deleted_posts.add((wiki_id, thread_id, post_id))
            continue

        # If the post does exist, record all post IDs seen in that page,
        # which are known to exist so don't need to be checked later
        existing_posts.update(post["id"] for post in thread_posts)

    return deleted_threads, deleted_posts
