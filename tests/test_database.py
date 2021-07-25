import pytest
from notifier.database import SqliteDriver


@pytest.fixture(scope="module")
def sample_database():
    db = SqliteDriver()
    sample_user_configs = [("1", "MyUsername", "hourly", "en")]
    sample_manual_subs = [
        ("1", "t-1", None, 1),
        ("1", "t-3", "p-32", 1),
        ("1", "t-4", None, -1),
    ]
    sample_wikis = [("my-wiki", 1)]
    sample_threads = [
        ("t-1", "Thread 1", "my-wiki"),
        ("t-2", "Thread 2", "my-wiki"),
        ("t-3", "Thread 3", "my-wiki"),
        ("t-4", "Thread 4", "my-wiki"),
    ]
    sample_posts = [
        ("p-11", "t-1", None, 10, "Post 1 1", "1", "MyUsername"),
        ("p-12", "t-1", None, 20, "Post 1 2", "2", "AUsername"),
        ("p-111", "t-1", "p-11", 30, "Post 1 1 1", "2", "AUsername"),
        ("p-21", "t-2", None, 13, "Post 2 1", "1", "MyUsername"),
        ("p-211", "t-2", "p-21", 17, "Post 2 1 1", "2", "AUsername"),
        ("p-212", "t-2", "p-21", 20, "Post 2 1 2", "3", "BUsername"),
        ("p-2121", "t-2", "p-212", 23, "Post 2 1 2 1", "1", "MyUsername"),
        ("p-31", "t-3", None, 16, "Post 3 1", "2", "AUsername"),
        ("p-32", "t-3", None, 21, "Post 3 2", "3", "BUsername"),
        ("p-321", "t-3", "p-32", 31, "Post 3 2 1", "2", "AUsername"),
        ("p-41", "t-4", None, 50, "Post 4 1", "1", "MyUsername"),
        ("p-411", "t-4", "p-41", 60, "Post 4 1 1", "3", "BUsername"),
        ("p-42", "t-4", None, 65, "Post 4 2", "3", "BUsername"),
    ]
    db.conn.executemany(
        "INSERT INTO user_configs VALUES (?, ?, ?, ?)", sample_user_configs
    )
    db.conn.executemany(
        "INSERT INTO manual_subs VALUES (?, ?, ?, ?)", sample_manual_subs
    )
    db.conn.executemany("INSERT INTO wikis VALUES (?, ?)", sample_wikis)
    db.conn.executemany("INSERT INTO threads VALUES (?, ?, ?)", sample_threads)
    db.conn.executemany(
        "INSERT INTO posts VALUES (?, ?, ?, ?, ? ,? ,?)", sample_posts
    )
    db.conn.commit()
    return db


def ids(posts):
    return set(p["posts.id"] for p in posts)


@pytest.fixture(scope="class")
def new_posts_for_user(sample_database):
    posts = sample_database.get_new_posts_for_user("1", 0)
    thread_posts = posts["thread_posts"]
    post_replies = posts["post_replies"]
    return thread_posts, post_replies


@pytest.fixture()
def thread_posts(new_posts_for_user):
    return new_posts_for_user[0]


@pytest.fixture()
def post_replies(new_posts_for_user):
    return new_posts_for_user[1]


def test_get_replied_posts(post_replies):
    assert ids(post_replies) == {"p-111", "p-211", "p-411"}


def test_get_post_reply_even_if_ignored_thread(post_replies):
    assert "p-411" in ids(post_replies)


def test_ignore_already_responded_post(post_replies, thread_posts):
    assert "p-212" not in ids(post_replies) | ids(thread_posts)


def test_ignore_own_post_in_thread(thread_posts):
    assert ids(thread_posts).isdisjoint({"p-11", "p-21", "p-2121" "p-41"})


def test_get_posts_in_threads(thread_posts):
    assert ids(thread_posts) == {"p-12", "p-111", "p-211"}


def test_prioritise_reply_deduplication(thread_posts):
    assert "p-111" not in ids(thread_posts)


def test_respect_ignored_thread(thread_posts):
    assert ids(thread_posts).isdisjoint({"p-41", "p-42"})
