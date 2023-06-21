from typing import Any, Callable, List, Optional, Set, Tuple

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
)


def construct(
    keys: List[str],
    all_values: List[Tuple[Any, ...]],
    *,
    verify: Optional[Callable[[Any], bool]] = None,
):
    """Constructs a DB entry from the given keys and value sets.

    Can also run a verification check on each value set given.
    """
    if verify:
        for values in all_values:
            assert verify(values)
    return [dict(zip(keys, values)) for values in all_values]


def subs(
    thread_id: str,
    post_id: str = None,
    direction: SubscriptionCardinality = 1,
) -> List[Subscription]:
    """Shorthand for constructing a single (un)subscription for a user."""
    return construct(
        ["thread_id", "post_id", "sub"], [(thread_id, post_id, direction)]
    )


def u(id: int, name: str, subs, unsubs, *, last_ts=1):
    """Shorthand for making a user shorthand for construct."""
    return (str(id), name, "hourly", "en", "pm", last_ts, "", subs, unsubs)


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
    sample_user_configs: List[RawUserConfig] = construct(
        [
            "user_id",
            "username",
            "frequency",
            "language",
            "delivery",
            "user_base_notified",
            "tags",
            "subscriptions",
            "unsubscriptions",
        ],
        [
            u(
                1,
                "UserR1",
                construct(
                    ["thread_id", "post_id", "sub"],
                    [("t-1", None, 1), ("t-3", "p-32", 1)],
                ),
                construct(
                    ["thread_id", "post_id", "sub"],
                    [("t-4", None, -1)],
                ),
            )
        ],
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
            ("t-0", "Null thread", "my-wiki", None, None, "system", 0),
            ("t-1", "Thread 1", "my-wiki", None, None, "UserR1", 10),
            ("t-2", "Thread 2", "my-wiki", None, None, "UserR1", 13),
            ("t-3", "Thread 3", "my-wiki", None, None, "UserD1", 16),
            ("t-4", "Thread 4", "my-wiki", None, None, "UserR1", 50),
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
            ("p-11", "t-1", None, 10, "Post 11", "", "1", "UserR1"),
            ("p-111", "t-1", "p-11", 30, "Post 111", "", "2", "UserD1"),
            ("p-12", "t-1", None, 20, "Post 12", "", "2", "UserD1"),
            #
            ("p-21", "t-2", None, 13, "Post 21", "", "1", "UserR1"),
            ("p-211", "t-2", "p-21", 17, "Post 211", "", "2", "UserD1"),
            ("p-212", "t-2", "p-21", 20, "Post 212", "", "3", "UserD2"),
            ("p-2121", "t-2", "p-212", 23, "Post 2121", "", "1", "UserR1"),
            #
            ("p-31", "t-3", None, 16, "Post 31", "", "2", "UserD1"),
            ("p-32", "t-3", None, 21, "Post 32", "", "3", "UserD2"),
            ("p-321", "t-3", "p-32", 31, "Post 321", "", "2", "UserD1"),
            #
            ("p-41", "t-4", None, 50, "Post 41", "", "1", "UserR1"),
            ("p-411", "t-4", "p-41", 60, "Post 411", "", "3", "UserD2"),
            ("p-42", "t-4", None, 65, "Post 42", "", "3", "UserD2"),
        ],
    )
    sample_channel_log: List[ChannelLogDump] = construct(
        [
            "channel",
            "start_timestamp",
            "end_timestamp",
            "user_count",
            "notified_user_count",
            "notified_post_count",
            "notified_thread_count",
        ],
        [("hourly", 30, 31, 5, 2, 10, 2), ("daily", 32, 33, 2, 0, 0, 0)],
    )
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


def titles(posts: List[PostReplyInfo]) -> Set[str]:
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


def test_counting(sample_database: BaseDatabaseDriver):
    """Test that the driver can count."""
    assert sample_database.count_supported_wikis() == 1
    assert sample_database.count_user_configs() == 1


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
    assert "p-111" not in [reply["id"] for reply in posts["post_replies"]]


def test_deleted_post(sample_database: BaseDatabaseDriver):
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


def test_get_notifiable_users(sample_database: BaseDatabaseDriver):
    """Test that the notifiable users list returns the correct set of users.

    The notifiable users utility lists directly from the database the set of
    users who have unsent notifications waiting for them, for a given channel.
    """
    # Let's add another test thread and some more subscribed users
    sample_user_configs: List[RawUserConfig] = construct(
        [
            "user_id",
            "username",
            "frequency",
            "language",
            "delivery",
            "user_base_notified",
            "tags",
            "subscriptions",
            "unsubscriptions",
        ],
        # Users scoped to this test are named like "Thread5User-<description>"
        [
            # Participated, but is manually unsubbed
            u(50, "T5U-Unsub", [], subs("t-5", None, -1)),
            # Did not participate, but is manually subbed
            u(51, "T5U-!P-Sub", subs("t-5"), []),
            # Posted but was not replied to
            u(52, "T5U-Lonely", [], []),
            # Started the thread
            u(53, "T5U-Starter", [], []),
            # Posted one reply, then replied to that reply
            u(54, "T5U-SelfRep", [], []),
            # Posted and was replied to
            u(55, "T5U-Poster", [], []),
            # Posted and was replied to, but is unsubbed from their post
            u(56, "T5U-UnsubPost", [], subs("t-5", "p-54", -1)),
            # Posted and was replied to, but has been notified already
            u(57, "T5U-PrevNotif", [], [], last_ts=200),
            # Irrelevant user who is subbed elsewhere
            u(58, "T5U-Irrel", subs("t-0"), []),
        ],
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
        [("t-5", "Thread 5", "my-wiki", None, None, "T5U-Starter", 100)],
    )

    def verify_post_author_id_matches_username(post: Tuple[Any, ...]) -> bool:
        """Check that the user ID+name pair match one of the scoped configs."""
        return any(
            post[6] == user["user_id"] and post[7] == user["username"]
            for user in sample_user_configs
        )

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
            ("p-51", "t-5", None, 100, "Post 51", "", "53", "T5U-Starter"),
            ("p-52", "t-5", None, 101, "Post 52", "", "55", "T5U-Poster"),
            ("p-521", "t-5", "p-52", 102, "Post 521", "", "52", "T5U-Lonely"),
            ("p-53", "t-5", None, 103, "Post 53", "", "54", "T5U-SelfRep"),
            ("p-531", "t-5", "p-53", 104, "Post 531", "", "54", "T5U-SelfRep"),
            ("p-54", "t-5", None, 106, "Post 54", "", "56", "T5U-UnsubPost"),
            ("p-541", "t-5", "p-54", 105, "Post 541", "", "52", "T5U-Lonely"),
            ("p-55", "t-5", None, 106, "Post 55", "", "50", "T5U-Unsub"),
            ("p-551", "t-5", "p-55", 107, "Post 551", "", "52", "T5U-Lonely"),
            ("p-56", "t-5", None, 108, "Post 56", "", "57", "T5U-PrevNotif"),
            ("p-561", "t-5", "p-56", 109, "Post 561", "", "52", "T5U-Lonely"),
        ],
        verify=verify_post_author_id_matches_username,
    )
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
