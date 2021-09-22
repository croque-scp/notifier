from typing import Any, List, Tuple

import pytest

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.drivers.mysql import MySqlDriver
from notifier.database.utils import resolve_driver_from_config
from notifier.types import (
    AuthConfig,
    LocalConfig,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
    ThreadInfo,
)


def construct(keys: List[str], all_values: List[Tuple[Any, ...]]):
    """pass"""
    return [dict(zip(keys, values)) for values in all_values]


@pytest.fixture(scope="module")
def sample_database(
    notifier_config: LocalConfig, notifier_auth: AuthConfig
) -> MySqlDriver:
    """Create a sample database with some fake interactions for testing."""
    Driver = resolve_driver_from_config(notifier_config["database"]["driver"])
    if Driver is not MySqlDriver:
        raise RuntimeError("Tests assume MySqlDriver")
    db_name = notifier_config["database"]["database_name"] + "_test"
    db = MySqlDriver(
        db_name,
        host=notifier_auth["mysql_host"],
        username=notifier_auth["mysql_username"],
        password=notifier_auth["mysql_password"],
    )
    db.scrub_database()
    subs: List[Subscription] = construct(
        ["thread_id", "post_id", "sub"],
        [("t-1", None, 1), ("t-3", "p-32", 1)],
    )
    unsubs: List[Subscription] = construct(
        ["thread_id", "post_id", "sub"],
        [("t-4", None, -1)],
    )
    sample_user_configs: List[RawUserConfig] = construct(
        [
            "user_id",
            "username",
            "frequency",
            "language",
            "delivery",
            "user_base_notified",
            "subscriptions",
            "unsubscriptions",
        ],
        [("1", "MyUser", "hourly", "en", "pm", 1, subs, unsubs)],
    )
    sample_wikis: List[SupportedWikiConfig] = construct(
        ["id", "name", "secure"], [("my-wiki", "My Wiki", 1)]
    )
    sample_threads: List[ThreadInfo] = construct(
        [
            "id",
            "title",
            "wiki_id",
            "category_id",
            "category_name",
            "creator_username",
            "created_timestamp",
        ],
        [
            ("t-1", "Thread 1", "my-wiki", None, None, "MyUser", 10, "p-11"),
            ("t-2", "Thread 2", "my-wiki", None, None, "MyUser", 13, "p-21"),
            ("t-3", "Thread 3", "my-wiki", None, None, "AUser", 16, "p-31"),
            ("t-4", "Thread 4", "my-wiki", None, None, "MyUser", 50, "p-41"),
        ],
    )
    sample_thread_first_posts = [
        ("t-1", "p-11"),
        ("t-2", "p-21"),
        ("t-3", "p-31"),
        ("t-4", "p-41"),
    ]
    sample_posts: List[RawPost] = construct(
        [
            "id",
            "thread_id",
            "parent_post_id",
            "posted_timestamp",
            "title",
            "snippet",
            "user_id",
            "username",
        ],
        [
            ("p-11", "t-1", None, 10, "Post 11", "", "1", "MyUser"),
            ("p-12", "t-1", None, 20, "Post 12", "", "2", "AUser"),
            ("p-111", "t-1", "p-11", 30, "Post 111", "", "2", "AUser"),
            ("p-21", "t-2", None, 13, "Post 21", "", "1", "MyUser"),
            ("p-211", "t-2", "p-21", 17, "Post 211", "", "2", "AUser"),
            ("p-212", "t-2", "p-21", 20, "Post 212", "", "3", "BUser"),
            ("p-2121", "t-2", "p-212", 23, "Post 2121", "", "1", "MyUser"),
            ("p-31", "t-3", None, 16, "Post 31", "", "2", "AUser"),
            ("p-32", "t-3", None, 21, "Post 32", "", "3", "BUser"),
            ("p-321", "t-3", "p-32", 31, "Post 321", "", "2", "AUser"),
            ("p-41", "t-4", None, 50, "Post 41", "", "1", "MyUser"),
            ("p-411", "t-4", "p-41", 60, "Post 411", "", "3", "BUser"),
            ("p-42", "t-4", None, 65, "Post 42", "", "3", "BUser"),
        ],
    )
    db.store_user_configs(sample_user_configs)
    db.store_supported_wikis(sample_wikis)
    for thread in sample_threads:
        db.store_thread(thread)
    for thread_id, post_id in sample_thread_first_posts:
        db.store_thread_first_post(thread_id, post_id)
    for post in sample_posts:
        db.store_post(post)
    return db


def titles(posts):
    """Get a set of post titles from a list of posts."""
    return set(p["title"] for p in posts)


@pytest.fixture(scope="class")
def new_posts_for_user(sample_database: BaseDatabaseDriver):
    """Extract new posts for a single user from the sample database."""
    posts = sample_database.get_new_posts_for_user("1", (0, 100))
    thread_posts = posts["thread_posts"]
    post_replies = posts["post_replies"]
    return thread_posts, post_replies


@pytest.fixture()
def thread_posts(new_posts_for_user):
    """Get only new thread posts for a user."""
    return new_posts_for_user[0]


@pytest.fixture()
def post_replies(new_posts_for_user):
    """Get only new post replies for a user."""
    return new_posts_for_user[1]


def test_get_replied_posts(post_replies):
    """Test that the post replies are as expected."""
    assert titles(post_replies) == {
        "Post 111",
        "Post 211",
        "Post 411",
        "Post 321",
    }


def test_get_post_reply_even_if_ignored_thread(post_replies):
    """Test that post replies are returned even if the thread is ignored."""
    assert "Post 411" in titles(post_replies)


def test_ignore_already_responded_post(post_replies, thread_posts):
    """Test that post replies are not returned if the user has already
    responded to them."""
    assert "Post 212" not in titles(post_replies) | titles(thread_posts)


def test_ignore_own_post_in_thread(thread_posts):
    """Test that the user is not notified of their own posts to a thread."""
    assert titles(thread_posts).isdisjoint(
        {"Post 11", "Post 21", "Post 2121", "Post 41"}
    )


def test_prioritise_reply_deduplication(thread_posts):
    """Test that, when a post would end up in both the thread posts and
    post replies, it only ends up in the post replies."""
    assert titles(thread_posts).isdisjoint({"Post 111", "Post 211"})


def test_get_posts_in_threads(thread_posts):
    """Test that thread posts are as expected."""
    assert titles(thread_posts) == {"Post 12"}


def test_respect_ignored_thread(thread_posts):
    """Test that posts in ignored threads do not appear as thread posts."""
    assert titles(thread_posts).isdisjoint({"Post 41", "Post 42"})


def test_new_threads(sample_database: BaseDatabaseDriver):
    """Test that the utility for checking if threads exists works."""
    assert sample_database.find_new_threads(["t-1", "t-2", "t-99"]) == ["t-99"]


def test_deleted_thread(sample_database: BaseDatabaseDriver):
    """Test that marking a thread as deleted works and that it then does
    not appear in notifications."""
    sample_database.mark_thread_as_deleted("t-1")
    posts = sample_database.get_new_posts_for_user("1", (0, 100))
    assert "t-1" not in [reply["thread_id"] for reply in posts["post_replies"]]
    assert "t-1" not in [post["thread_id"] for post in posts["thread_posts"]]


def test_initial_notified_timestamp(sample_database: MySqlDriver):
    """Test that the initial last notified timestamp for a user is set."""
    with sample_database.transaction() as cursor:

        def check_timestamp(n):
            cursor.execute(
                """
                SELECT notified_timestamp
                FROM user_last_notified
                WHERE user_id='1'
                """
            )
            assert (cursor.fetchone() or {})["notified_timestamp"] == n

        check_timestamp(1)
        sample_database.execute_named(
            "store_user_last_notified",
            {
                "user_id": "1",
                "notified_timestamp": 2,
            },
        )
        check_timestamp(2)
        sample_database.execute_named(
            "store_new_user_last_notified",
            {
                "user_id": "1",
                "notified_timestamp": 3,
            },
        )
        check_timestamp(2)
