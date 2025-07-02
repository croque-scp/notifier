from unittest.mock import MagicMock
import pytest
from notifier.database.drivers.mysql import MySqlDriver
from notifier.deletions import clear_deleted_posts
from notifier.types import PostMeta
from notifier.database.drivers.base import BaseDatabaseDriver
import time
from notifier.types import (
    NotifiablePost,
    Context,
    RawUserConfig,
    SupportedWikiConfig,
)
from notifier.database.utils import resolve_driver_from_config
from notifier.types import AuthConfig, LocalConfig


@pytest.fixture(scope="module")
def deletions_test_database(
    notifier_config: LocalConfig, notifier_auth: AuthConfig
) -> BaseDatabaseDriver:
    """Create a database with posts at controlled, recent timestamps for deletion tests."""
    Driver = resolve_driver_from_config(notifier_config["database"]["driver"])
    if Driver is not MySqlDriver:
        raise RuntimeError("Tests assume MySqlDriver")
    db_name = notifier_config["database"]["database_name"] + "_test"
    db = Driver(
        db_name,
        host=notifier_auth["mysql_host"],
        username=notifier_auth["mysql_username"],
        password=notifier_auth["mysql_password"],
    )
    db.scrub_database()
    now = int(time.time())
    # Add a wiki, thread, and parent post context
    db.store_supported_wikis(
        [{"id": "test-wiki", "name": "Test Wiki", "secure": 1}]
    )
    db.store_context_thread(
        {
            "thread_id": "thread-1",
            "thread_title": "Thread 1",
            "thread_created_timestamp": now - 1000,
            "thread_snippet": "",
            "thread_creator_username": "user1",
            "first_post_id": "post-1",
            "first_post_author_user_id": "user1",
            "first_post_author_username": "user1",
            "first_post_created_timestamp": now - 1000,
        }
    )
    db.store_context_parent_post(
        {
            "post_id": "post-1",
            "posted_timestamp": now - 1000,
            "post_title": "Post 1",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
        }
    )
    # Add posts at specific times that should and should not be selected by get_posts_to_check_for_deletion
    posts: list[NotifiablePost] = [
        # This post should be selected (within the 3 hour window)
        {
            "post_id": "post-should-check",
            "posted_timestamp": now - 2 * 3600,  # 2 hours ago
            "post_title": "Should Check",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
            "context_wiki_id": "test-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "thread-1",
            "context_parent_post_id": None,
        },
        # This post should NOT be selected (too old)
        {
            "post_id": "post-too-old",
            "posted_timestamp": now - 10 * 3600,  # 10 hours ago
            "post_title": "Too Old",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
            "context_wiki_id": "test-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "thread-1",
            "context_parent_post_id": None,
        },
        # This post should be selected (in the 5-6 hour window)
        {
            "post_id": "post-should-check2",
            "posted_timestamp": now - 5 * 3600 - 1800,  # 5.5 hours ago
            "post_title": "Should Check 2",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
            "context_wiki_id": "test-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "thread-1",
            "context_parent_post_id": None,
        },
    ]
    for post in posts:
        db.store_post(post)
    return db


@pytest.mark.needs_database
def test_clear_deleted_posts_checks_expected_posts(
    deletions_test_database: BaseDatabaseDriver, mocker: MagicMock
) -> None:
    """Test that `clear_deleted_posts` checks the expected posts for deletion using controlled timestamps."""
    from notifier.deletions import clear_deleted_posts

    mock_wikidot = MagicMock()
    called_posts = []

    def fake_delete_posts(
        posts: list[PostMeta], database: BaseDatabaseDriver, wikidot: MagicMock
    ) -> None:
        called_posts.extend(posts)

    mocker.patch(
        "notifier.deletions.delete_posts", side_effect=fake_delete_posts
    )
    clear_deleted_posts(deletions_test_database, mock_wikidot)
    import datetime
    from notifier import timing

    now_hour = timing.now.replace(minute=0, second=0, microsecond=0)
    now_hour_ts = int(datetime.datetime.timestamp(now_hour))
    expected_posts = deletions_test_database.get_posts_to_check_for_deletion(
        now_hour_ts
    )
    assert called_posts == expected_posts
