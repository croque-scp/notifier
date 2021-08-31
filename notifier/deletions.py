import time
from typing import List, Set, Tuple

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.wikiconnection import Connection, ThreadNotExists


def clear_deleted_threads(
    frequency: str, database: BaseDatabaseDriver, connection: Connection
):
    """Remove deleted threads from the database.

    For each thread that a user on the given channel would soon be
    notified about, check that it still exists. If it does not, flag it as
    deleted in the cache, preventing it from emitting any notifications.

    If no users were about to be notified about a thread, there is no point
    bothering to look up whether it still exists or not.
    """
    print(f"Clearing deleted threads from the {frequency} channel")
    now = int(time.time())
    users = database.get_user_configs(frequency)
    threads: Set[Tuple[str, str, str]] = set()
    for user in users:
        posts = database.get_new_posts_for_user(
            user["user_id"], (user["last_notified_timestamp"], now)
        )
        for post in posts["thread_posts"]:
            threads.add((post["wiki_id"], post["thread_id"], post["id"]))
        for reply in posts["post_replies"]:
            threads.add((reply["wiki_id"], reply["thread_id"], reply["id"]))
    print(f"Found {len(threads)} threads to check")
    deleted_threads: List[Tuple[str, str]] = []
    deleted_posts: List[Tuple[str, str, str]] = []
    for wiki_id, thread_id, post_id in threads:
        # Construct the iterator for thread pages
        thread_pages = connection.thread(wiki_id, thread_id, post_id)
        try:
            # The first iteration is a special case and returns information
            # about the thread; it will always succeed if the thread exists
            next(thread_pages)
        except ThreadNotExists:
            database.mark_thread_as_deleted(thread_id)
            deleted_threads.append((wiki_id, thread_id))
            continue
        try:
            # Second iteration returns the first post from the targeted
            # page; if there are no posts it means the targeted page
            # doesn't exist and therefore neither does the targeted post
            next(thread_pages)
        except StopIteration:
            database.mark_post_as_deleted(post_id)
            deleted_posts.append((wiki_id, thread_id, post_id))
            continue

        # If the post does exist, record all post IDs seen in that page,
        # which are known to exist and don't need to be checked
        # TODO
        # Actually I don't think this will work the way I've implemented
        # thing because Connection.thread returns a generator of posts, not
        # of pages - I guess I need to call the method it uses internally
        # directly
    print(f"Deleted {len(deleted_threads)} threads")
    print(
        f"Deleted {len(deleted_posts)} posts "
        f"in {len(set(d[1] for d in deleted_posts))} threads"
    )
