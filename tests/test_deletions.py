from datetime import datetime
from unittest.mock import MagicMock
import pytest

from notifier import timing
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.drivers.mysql import MySqlDriver
from notifier.database.utils import resolve_driver_from_config
from notifier.deletions import clear_deleted_posts, delete_posts
from notifier.types import (
    AuthConfig,
    LocalConfig,
    NotifiablePost,
    PostMeta,
)


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
    # Use the same hour-rounded 'now' as the production code
    now_hour = timing.now.replace(minute=0, second=0, microsecond=0)
    now = int(datetime.timestamp(now_hour))
    # Add a wiki, thread, and parent post context
    db.store_supported_wikis(
        [{"id": "test-wiki", "name": "Test Wiki", "secure": 1}]
    )
    db.store_context_thread(
        {
            "thread_id": "t-1",
            "thread_title": "Thread 1",
            "thread_created_timestamp": now - 1000,
            "thread_snippet": "",
            "thread_creator_username": "user1",
            "first_post_id": "p-1",
            "first_post_author_user_id": "user1",
            "first_post_author_username": "user1",
            "first_post_created_timestamp": now - 1000,
        }
    )
    db.store_context_parent_post(
        {
            "post_id": "p-1",
            "posted_timestamp": now - 1000,
            "post_title": "Post 1",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
        }
    )
    # Add posts at specific times that should and should not be selected by get_posts_to_check_for_deletion
    posts: list[NotifiablePost] = [
        # Should be selected (0-3 hour window)
        {
            "post_id": "p-1",
            "posted_timestamp": now - 2 * 3600,  # 2 hours ago
            "post_title": "Should Check 1",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
            "context_wiki_id": "test-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-1",
            "context_parent_post_id": None,
        },
        # Should be selected (5-6 hour window)
        {
            "post_id": "p-2",
            "posted_timestamp": now - (5 * 3600) - 1800,  # 5.5 hours ago
            "post_title": "Should Check 2",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
            "context_wiki_id": "test-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-1",
            "context_parent_post_id": None,
        },
        # Should NOT be selected (in gap between windows)
        {
            "post_id": "p-3",
            "posted_timestamp": now - 4 * 3600,  # between 3-5 hour windows
            "post_title": "Should Not Check",
            "post_snippet": "",
            "author_user_id": "user1",
            "author_username": "user1",
            "context_wiki_id": "test-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-1",
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
    mock_wikidot = MagicMock()
    called_posts = []

    def fake_delete_posts(
        posts: list[PostMeta],
        _database: BaseDatabaseDriver,
        _wikidot: MagicMock,
    ) -> None:
        called_posts.extend(posts)

    mocker.patch(
        "notifier.deletions.delete_posts", side_effect=fake_delete_posts
    )
    clear_deleted_posts(deletions_test_database, mock_wikidot)
    expected_post_ids = {
        "p-1",  # 2 hours ago (0-3 hour window)
        "p-2",  # 5.5 hours ago (5-6 hour window)
    }
    actual_post_ids = {post["post_id"] for post in called_posts}
    assert actual_post_ids == expected_post_ids


@pytest.mark.needs_database
def test_delete_posts_with_existing_post(
    deletions_test_database: BaseDatabaseDriver, mocker: MagicMock
) -> None:
    """Test that delete_posts doesn't delete posts that still exist remotely."""
    mock_wikidot = MagicMock()

    # Thread exists and contains the post we're checking
    thread_meta = {
        "current_page": 1,
        "created_timestamp": 1000000000,
        "title": "Test Thread",
        "creator_username": "user1",
    }
    thread_posts = [
        {
            "id": "post-exists",
            "snippet": "This post exists",
            "user_id": "user1",
            "username": "user1",
            "posted_timestamp": 1000000000,
        }
    ]
    mock_wikidot.thread.return_value = (thread_meta, thread_posts)
    posts: list[PostMeta] = [
        {
            "wiki_id": "test-wiki",
            "thread_id": "thread-1",
            "post_id": "post-exists",
        }
    ]
    delete_post_spy = mocker.spy(deletions_test_database, "delete_post")
    store_context_thread_spy = mocker.spy(
        deletions_test_database, "store_context_thread"
    )
    delete_posts(posts, deletions_test_database, mock_wikidot)
    delete_post_spy.assert_not_called()

    # Thread context should be updated since it's page 1
    store_context_thread_spy.assert_called_once()


@pytest.mark.needs_database
def test_delete_posts_with_empty_thread(
    deletions_test_database: BaseDatabaseDriver, mocker: MagicMock
) -> None:
    """Test that delete_posts treats empty threads as deleted."""
    mock_wikidot = MagicMock()
    mock_wikidot.thread.return_value = (
        {
            "current_page": 1,
            "created_timestamp": 1000000000,
            "title": "Empty Thread",
            "creator_username": "user1",
        },
        [],  # No posts
    )
    posts: list[PostMeta] = [
        {
            "wiki_id": "test-wiki",
            "thread_id": "thread-empty",
            "post_id": "post-in-empty-thread",
        }
    ]
    delete_context_thread_spy = mocker.spy(
        deletions_test_database, "delete_context_thread"
    )
    delete_posts(posts, deletions_test_database, mock_wikidot)
    delete_context_thread_spy.assert_called_once_with("thread-empty")


@pytest.mark.needs_database
def test_delete_posts_with_missing_post(
    deletions_test_database: BaseDatabaseDriver, mocker: MagicMock
) -> None:
    """Test that delete_posts deletes posts that don't exist remotely."""
    mock_wikidot = MagicMock()
    thread_meta = {
        "current_page": 2,
        "created_timestamp": 1000000000,
        "title": "Test Thread",
        "creator_username": "user1",
    }
    # Thread exists but doesn't contain the post we're checking
    thread_posts = [
        {
            "id": "other-post",
            "snippet": "Some other post",
            "user_id": "user2",
            "username": "user2",
            "posted_timestamp": 1000000001,
        }
    ]
    mock_wikidot.thread.return_value = (thread_meta, thread_posts)
    posts: list[PostMeta] = [
        {
            "wiki_id": "test-wiki",
            "thread_id": "thread-1",
            "post_id": "missing-post",
        }
    ]
    delete_post_spy = mocker.spy(deletions_test_database, "delete_post")
    delete_posts(posts, deletions_test_database, mock_wikidot)
    delete_post_spy.assert_called_once_with("missing-post")
