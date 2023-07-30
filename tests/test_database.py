from typing import List, Optional, Sequence, Set, Tuple

import pytest

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.drivers.mysql import MySqlDriver
from notifier.database.utils import resolve_driver_from_config
from notifier.types import (
    ActivationLogDump,
    AuthConfig,
    ChannelLogDump,
    LocalConfig,
    PostReplyInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SubscriptionCardinality,
    SupportedWikiConfig,
    ThreadInfo,
    ThreadPostInfo,
)


def sub(
    thread_id: str,
    post_id: Optional[str] = None,
    direction: SubscriptionCardinality = 1,
) -> Subscription:
    """Shorthand for constructing a single (un)subscription for a user."""
    return {"thread_id": thread_id, "post_id": post_id, "sub": direction}


def u(
    user_id: int,
    name: str,
    subs: List[Subscription],
    unsubs: List[Subscription],
    *,
    last_ts: int = 1,
) -> RawUserConfig:
    """Shorthand for making a user shorthand for construct."""
    return {
        "user_id": str(user_id),
        "username": name,
        "frequency": "hourly",
        "language": "en",
        "delivery": "pm",
        "user_base_notified": last_ts,
        "tags": "",
        "subscriptions": subs,
        "unsubscriptions": unsubs,
    }


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
    sample_user_configs: List[RawUserConfig] = [
        u(
            1,
            "UserR1",
            [sub("t-1", None, 1), sub("t-3", "p-32", 1)],
            [sub("t-4", None, -1)],
        ),
    ]
    sample_wikis: List[SupportedWikiConfig] = [
        {"id": "my-wiki", "name": "My Wiki", "secure": 1}
    ]
    sample_threads: List[ThreadInfo] = [
        {
            "id": "t-0",
            "title": "Null thread",
            "wiki_id": "my-wiki",
            "category_id": None,
            "category_name": None,
            "creator_username": "system",
            "created_timestamp": 0,
        },
        {
            "id": "t-1",
            "title": "Thread 1",
            "wiki_id": "my-wiki",
            "category_id": None,
            "category_name": None,
            "creator_username": "UserR1",
            "created_timestamp": 10,
        },
        {
            "id": "t-2",
            "title": "Thread 2",
            "wiki_id": "my-wiki",
            "category_id": None,
            "category_name": None,
            "creator_username": "UserR1",
            "created_timestamp": 13,
        },
        {
            "id": "t-3",
            "title": "Thread 3",
            "wiki_id": "my-wiki",
            "category_id": None,
            "category_name": None,
            "creator_username": "UserD1",
            "created_timestamp": 16,
        },
        {
            "id": "t-4",
            "title": "Thread 4",
            "wiki_id": "my-wiki",
            "category_id": None,
            "category_name": None,
            "creator_username": "UserR1",
            "created_timestamp": 50,
        },
    ]
    sample_thread_first_posts = [
        ("t-1", "p-11"),
        ("t-2", "p-21"),
        ("t-3", "p-31"),
        ("t-4", "p-41"),
    ]
    sample_posts: List[RawPost] = [
        {
            "id": "p-11",
            "thread_id": "t-1",
            "parent_post_id": None,
            "posted_timestamp": 10,
            "title": "Post 11",
            "snippet": "",
            "user_id": "1",
            "username": "UserR1",
        },
        {
            "id": "p-111",
            "thread_id": "t-1",
            "parent_post_id": "p-11",
            "posted_timestamp": 30,
            "title": "Post 111",
            "snippet": "",
            "user_id": "2",
            "username": "UserD1",
        },
        {
            "id": "p-12",
            "thread_id": "t-1",
            "parent_post_id": None,
            "posted_timestamp": 20,
            "title": "Post 12",
            "snippet": "",
            "user_id": "2",
            "username": "UserD1",
        },
        {
            "id": "p-21",
            "thread_id": "t-2",
            "parent_post_id": None,
            "posted_timestamp": 13,
            "title": "Post 21",
            "snippet": "",
            "user_id": "1",
            "username": "UserR1",
        },
        {
            "id": "p-211",
            "thread_id": "t-2",
            "parent_post_id": "p-21",
            "posted_timestamp": 17,
            "title": "Post 211",
            "snippet": "",
            "user_id": "2",
            "username": "UserD1",
        },
        {
            "id": "p-212",
            "thread_id": "t-2",
            "parent_post_id": "p-21",
            "posted_timestamp": 20,
            "title": "Post 212",
            "snippet": "",
            "user_id": "3",
            "username": "UserD2",
        },
        {
            "id": "p-2121",
            "thread_id": "t-2",
            "parent_post_id": "p-212",
            "posted_timestamp": 23,
            "title": "Post 2121",
            "snippet": "",
            "user_id": "1",
            "username": "UserR1",
        },
        {
            "id": "p-31",
            "thread_id": "t-3",
            "parent_post_id": None,
            "posted_timestamp": 16,
            "title": "Post 31",
            "snippet": "",
            "user_id": "2",
            "username": "UserD1",
        },
        {
            "id": "p-32",
            "thread_id": "t-3",
            "parent_post_id": None,
            "posted_timestamp": 21,
            "title": "Post 32",
            "snippet": "",
            "user_id": "3",
            "username": "UserD2",
        },
        {
            "id": "p-321",
            "thread_id": "t-3",
            "parent_post_id": "p-32",
            "posted_timestamp": 31,
            "title": "Post 321",
            "snippet": "",
            "user_id": "2",
            "username": "UserD1",
        },
        {
            "id": "p-41",
            "thread_id": "t-4",
            "parent_post_id": None,
            "posted_timestamp": 50,
            "title": "Post 41",
            "snippet": "",
            "user_id": "1",
            "username": "UserR1",
        },
        {
            "id": "p-411",
            "thread_id": "t-4",
            "parent_post_id": "p-41",
            "posted_timestamp": 60,
            "title": "Post 411",
            "snippet": "",
            "user_id": "3",
            "username": "UserD2",
        },
        {
            "id": "p-42",
            "thread_id": "t-4",
            "parent_post_id": None,
            "posted_timestamp": 65,
            "title": "Post 42",
            "snippet": "",
            "user_id": "3",
            "username": "UserD2",
        },
    ]
    sample_channel_log: List[ChannelLogDump] = [
        {
            "channel": "hourly",
            "start_timestamp": 30,
            "end_timestamp": 31,
            "user_count": 5,
            "notified_user_count": 2,
            "notified_post_count": 10,
            "notified_thread_count": 2,
        },
        {
            "channel": "daily",
            "start_timestamp": 32,
            "end_timestamp": 33,
            "user_count": 2,
            "notified_user_count": 0,
            "notified_post_count": 0,
            "notified_thread_count": 0,
        },
    ]
    sample_activation_log: ActivationLogDump = {
        "start_timestamp": 0,
        "config_start_timestamp": 0,
        "config_end_timestamp": 0,
        "getpost_start_timestamp": 0,
        "getpost_end_timestamp": 0,
        "notify_start_timestamp": 0,
        "notify_end_timestamp": 0,
        "end_timestamp": 0,
        "new_post_count": 0,
        "new_thread_count": 0,
        "checked_thread_count": 0,
        "site_count": 0,
        "user_count": 0,
        "post_count": 0,
        "thread_count": 0,
    }
    db.store_user_configs(sample_user_configs)
    db.store_supported_wikis(sample_wikis)
    for thread in sample_threads:
        db.store_thread(thread)
    for thread_id, post_id in sample_thread_first_posts:
        db.store_thread_first_post(thread_id, post_id)
    for post in sample_posts:
        db.store_post(post)
    for channel_log in sample_channel_log:
        db.store_channel_log_dump(channel_log)
    db.store_activation_log_dump(sample_activation_log)
    return db


def titles(posts: Sequence[ThreadPostInfo]) -> Set[str]:
    """Get a set of post titles from a list of posts."""
    return set(p["title"] for p in posts)


@pytest.fixture(scope="class")
def new_posts_for_user(
    sample_database: BaseDatabaseDriver,
) -> Tuple[List[ThreadPostInfo], List[PostReplyInfo]]:
    """Extract new posts for a single user from the sample database."""
    posts = sample_database.get_new_posts_for_user("1", (0, 100))
    thread_posts = posts["thread_posts"]
    post_replies = posts["post_replies"]
    return thread_posts, post_replies


@pytest.fixture()
def thread_posts(
    new_posts_for_user: Tuple[List[ThreadPostInfo], List[PostReplyInfo]]
) -> List[ThreadPostInfo]:
    """Get only new thread posts for a user."""
    return new_posts_for_user[0]


@pytest.fixture()
def post_replies(
    new_posts_for_user: Tuple[List[ThreadPostInfo], List[PostReplyInfo]]
) -> List[PostReplyInfo]:
    """Get only new post replies for a user."""
    return new_posts_for_user[1]


@pytest.mark.needs_database
def test_counting(sample_database: BaseDatabaseDriver) -> None:
    """Test that the driver can count."""
    assert sample_database.count_supported_wikis() == 1
    assert sample_database.count_user_configs() == 1


@pytest.mark.needs_database
def test_get_replied_posts(post_replies: List[PostReplyInfo]) -> None:
    """Test that the post replies are as expected."""
    assert titles(post_replies) == {
        "Post 111",
        "Post 211",
        "Post 411",
        "Post 321",
    }


@pytest.mark.needs_database
def test_get_post_reply_even_if_ignored_thread(
    post_replies: List[PostReplyInfo],
) -> None:
    """Test that post replies are returned even if the thread is ignored."""
    assert "Post 411" in titles(post_replies)


@pytest.mark.needs_database
def test_ignore_already_responded_post(
    post_replies: List[PostReplyInfo], thread_posts: List[ThreadPostInfo]
) -> None:
    """Test that post replies are not returned if the user has already
    responded to them."""
    assert "Post 212" not in titles(post_replies) | titles(thread_posts)


@pytest.mark.needs_database
def test_ignore_own_post_in_thread(thread_posts: List[ThreadPostInfo]) -> None:
    """Test that the user is not notified of their own posts to a thread."""
    assert titles(thread_posts).isdisjoint(
        {"Post 11", "Post 21", "Post 2121", "Post 41"}
    )


@pytest.mark.needs_database
def test_prioritise_reply_deduplication(
    thread_posts: List[ThreadPostInfo],
) -> None:
    """Test that, when a post would end up in both the thread posts and
    post replies, it only ends up in the post replies."""
    assert titles(thread_posts).isdisjoint({"Post 111", "Post 211"})


@pytest.mark.needs_database
def test_get_posts_in_threads(thread_posts: List[ThreadPostInfo]) -> None:
    """Test that thread posts are as expected."""
    assert titles(thread_posts) == {"Post 12"}


@pytest.mark.needs_database
def test_respect_ignored_thread(thread_posts: List[ThreadPostInfo]) -> None:
    """Test that posts in ignored threads do not appear as thread posts."""
    assert titles(thread_posts).isdisjoint({"Post 41", "Post 42"})


@pytest.mark.needs_database
def test_new_threads(sample_database: BaseDatabaseDriver) -> None:
    """Test that the utility for checking if threads exists works."""
    assert sample_database.find_new_threads(["t-1", "t-2", "t-99"]) == ["t-99"]


@pytest.mark.needs_database
def test_deleted_thread(sample_database: BaseDatabaseDriver) -> None:
    """Test that marking a thread as deleted works and that it then does
    not appear in notifications."""
    sample_database.mark_thread_as_deleted("t-1")
    posts = sample_database.get_new_posts_for_user("1", (0, 100))
    assert "t-1" not in [reply["thread_id"] for reply in posts["post_replies"]]
    assert "t-1" not in [post["thread_id"] for post in posts["thread_posts"]]
    assert "p-111" not in [reply["id"] for reply in posts["post_replies"]]


@pytest.mark.needs_database
def test_deleted_post(sample_database: BaseDatabaseDriver) -> None:
    """Test that marking a post as deleted works and that it then does
    not appear in notifications."""
    # p-21 would not appear in a notification anyway because it was made by
    # the testing user, put p-211 would, and should have been recursively
    # marked as deleted
    posts = sample_database.get_new_posts_for_user("1", (0, 100))
    assert "p-211" in [reply["id"] for reply in posts["post_replies"]]
    sample_database.mark_post_as_deleted("p-21")
    posts = sample_database.get_new_posts_for_user("1", (0, 100))
    assert "p-211" not in [reply["id"] for reply in posts["post_replies"]]


@pytest.mark.needs_database
def test_initial_notified_timestamp(sample_database: MySqlDriver) -> None:
    """Test that the initial last notified timestamp for a user is set."""
    with sample_database.transaction() as cursor:

        def check_timestamp(n: int) -> None:
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


@pytest.mark.needs_database
def test_get_notifiable_users(sample_database: BaseDatabaseDriver) -> None:
    """Test that the notifiable users list returns the correct set of users.

    The notifiable users utility lists directly from the database the set of
    users who have unsent notifications waiting for them, for a given channel.
    """
    # Let's add another test thread and some more subscribed users
    sample_user_configs: List[RawUserConfig] = [
        # Users scoped to this test are named like "Thread5User-<description>"
        # Participated, but is manually unsubbed
        u(50, "T5U-Unsub", [], [sub("t-5", None, -1)]),
        # Did not participate, but is manually subbed
        u(51, "T5U-!P-Sub", [sub("t-5")], []),
        # Posted but was not replied to
        u(52, "T5U-Lonely", [], []),
        # Started the thread
        u(53, "T5U-Starter", [], []),
        # Posted one reply, then replied to that reply
        u(54, "T5U-SelfRep", [], []),
        # Posted and was replied to
        u(55, "T5U-Poster", [], []),
        # Posted and was replied to, but is unsubbed from their post
        u(56, "T5U-UnsubPost", [], [sub("t-5", "p-54", -1)]),
        # Posted and was replied to, but has been notified already
        u(57, "T5U-PrevNotif", [], [], last_ts=200),
        # Irrelevant user who is subbed elsewhere
        u(58, "T5U-Irrel", [sub("t-0")], []),
    ]
    sample_threads: List[ThreadInfo] = [
        {
            "id": "t-5",
            "title": "Thread 5",
            "wiki_id": "my-wiki",
            "category_id": None,
            "category_name": None,
            "creator_username": "T5U-Starter",
            "created_timestamp": 100,
        }
    ]

    sample_posts: List[RawPost] = [
        {
            "id": "p-51",
            "thread_id": "t-5",
            "parent_post_id": None,
            "posted_timestamp": 100,
            "title": "Post 51",
            "snippet": "",
            "user_id": "53",
            "username": "T5U-Starter",
        },
        {
            "id": "p-52",
            "thread_id": "t-5",
            "parent_post_id": None,
            "posted_timestamp": 101,
            "title": "Post 52",
            "snippet": "",
            "user_id": "55",
            "username": "T5U-Poster",
        },
        {
            "id": "p-521",
            "thread_id": "t-5",
            "parent_post_id": "p-52",
            "posted_timestamp": 102,
            "title": "Post 521",
            "snippet": "",
            "user_id": "52",
            "username": "T5U-Lonely",
        },
        {
            "id": "p-53",
            "thread_id": "t-5",
            "parent_post_id": None,
            "posted_timestamp": 103,
            "title": "Post 53",
            "snippet": "",
            "user_id": "54",
            "username": "T5U-SelfRep",
        },
        {
            "id": "p-531",
            "thread_id": "t-5",
            "parent_post_id": "p-53",
            "posted_timestamp": 104,
            "title": "Post 531",
            "snippet": "",
            "user_id": "54",
            "username": "T5U-SelfRep",
        },
        {
            "id": "p-54",
            "thread_id": "t-5",
            "parent_post_id": None,
            "posted_timestamp": 106,
            "title": "Post 54",
            "snippet": "",
            "user_id": "56",
            "username": "T5U-UnsubPost",
        },
        {
            "id": "p-541",
            "thread_id": "t-5",
            "parent_post_id": "p-54",
            "posted_timestamp": 105,
            "title": "Post 541",
            "snippet": "",
            "user_id": "52",
            "username": "T5U-Lonely",
        },
        {
            "id": "p-55",
            "thread_id": "t-5",
            "parent_post_id": None,
            "posted_timestamp": 106,
            "title": "Post 55",
            "snippet": "",
            "user_id": "50",
            "username": "T5U-Unsub",
        },
        {
            "id": "p-551",
            "thread_id": "t-5",
            "parent_post_id": "p-55",
            "posted_timestamp": 107,
            "title": "Post 551",
            "snippet": "",
            "user_id": "52",
            "username": "T5U-Lonely",
        },
        {
            "id": "p-56",
            "thread_id": "t-5",
            "parent_post_id": None,
            "posted_timestamp": 108,
            "title": "Post 56",
            "snippet": "",
            "user_id": "57",
            "username": "T5U-PrevNotif",
        },
        {
            "id": "p-561",
            "thread_id": "t-5",
            "parent_post_id": "p-56",
            "posted_timestamp": 109,
            "title": "Post 561",
            "snippet": "",
            "user_id": "52",
            "username": "T5U-Lonely",
        },
    ]

    for post in sample_posts:
        if not any(
            post["user_id"] == user["user_id"]
            and post["username"] == user["username"]
            for user in sample_user_configs
        ):
            raise Exception("Bad name")

    # verify=verify_post_author_id_matches_username
    sample_database.store_user_configs(
        sample_user_configs, overwrite_existing=False
    )
    for thread in sample_threads:
        sample_database.store_thread(thread)
    sample_database.store_thread_first_post("t-5", "p-51")
    for post in sample_posts:
        sample_database.store_post(post)

    users_expected_to_have_notifications = {
        "1",  # UserR1 from base sample DB
        "51",  # T5U-!P-Sub
        "53",  # T5U-Starter
        "55",  # T5U-Poster
    }

    users_with_notifications = sample_database.get_notifiable_users("hourly")

    assert (
        set(users_with_notifications) == users_expected_to_have_notifications
    )
