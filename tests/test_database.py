import pytest

from notifier.database.drivers import DatabaseDriver
from notifier.database.drivers.base import BaseDatabaseDriver


@pytest.fixture(scope="module")
def sample_database():
    """Create a sample database with some fake interactions for testing."""
    db = DatabaseDriver()
    sample_user_configs = [("1", "MyUsername", "hourly", "en", "pm")]
    sample_manual_subs = [
        ("1", "t-1", None, 1),
        ("1", "t-3", "p-32", 1),
        ("1", "t-4", None, -1),
    ]
    sample_wikis = [("my-wiki", "My Wiki", 1)]
    sample_threads = [
        ("t-1", "Thread 1", "my-wiki", None, None, 10),
        ("t-2", "Thread 2", "my-wiki", None, None, 13),
        ("t-3", "Thread 3", "my-wiki", None, None, 16),
        ("t-4", "Thread 4", "my-wiki", None, None, 50),
    ]
    sample_posts = [
        ("p-11", "t-1", None, 10, "Post 11", "", "1", "MyUsername"),
        ("p-12", "t-1", None, 20, "Post 12", "", "2", "AUsername"),
        ("p-111", "t-1", "p-11", 30, "Post 111", "", "2", "AUsername"),
        ("p-21", "t-2", None, 13, "Post 21", "", "1", "MyUsername"),
        ("p-211", "t-2", "p-21", 17, "Post 211", "", "2", "AUsername"),
        ("p-212", "t-2", "p-21", 20, "Post 212", "", "3", "BUsername"),
        ("p-2121", "t-2", "p-212", 23, "Post 2121", "", "1", "MyUsername"),
        ("p-31", "t-3", None, 16, "Post 31", "", "2", "AUsername"),
        ("p-32", "t-3", None, 21, "Post 32", "", "3", "BUsername"),
        ("p-321", "t-3", "p-32", 31, "Post 321", "", "2", "AUsername"),
        ("p-41", "t-4", None, 50, "Post 41", "", "1", "MyUsername"),
        ("p-411", "t-4", "p-41", 60, "Post 411", "", "3", "BUsername"),
        ("p-42", "t-4", None, 65, "Post 42", "", "3", "BUsername"),
    ]
    db.conn.executemany(
        "INSERT INTO user_config VALUES (?, ?, ?, ?, ?)", sample_user_configs
    )
    db.conn.executemany(
        "INSERT INTO manual_sub VALUES (?, ?, ?, ?)", sample_manual_subs
    )
    db.conn.executemany("INSERT INTO wiki VALUES (?, ?, ?)", sample_wikis)
    db.conn.executemany(
        "INSERT INTO thread VALUES (?, ?, ?, ?, ?, ?)", sample_threads
    )
    db.conn.executemany(
        "INSERT INTO post VALUES (?, ?, ?, ?, ?, ?, ?, ?)", sample_posts
    )
    db.conn.commit()
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
