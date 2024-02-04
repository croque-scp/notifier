from typing import List, Optional, Sequence, Set

import pytest

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.drivers.mysql import MySqlDriver
from notifier.database.utils import resolve_driver_from_config
from notifier.types import (
    ActivationLogDump,
    AuthConfig,
    ChannelLogDump,
    Context,
    LocalConfig,
    NotifiablePost,
    PostInfo,
    RawUserConfig,
    Subscription,
    SubscriptionCardinality,
    SupportedWikiConfig,
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
    sample_threads: List[Context.Thread] = [
        {
            "thread_id": "t-1",
            "thread_title": "Thread 1",
            "thread_created_timestamp": 10,
            "thread_snippet": "",
            "thread_creator_username": "UserR1",
            "first_post_id": "p-11",
            "first_post_author_user_id": "1",
            "first_post_author_username": "UserR1",
            "first_post_created_timestamp": 10,
        },
        {
            "thread_id": "t-2",
            "thread_title": "Thread 2",
            "thread_created_timestamp": 13,
            "thread_snippet": "",
            "thread_creator_username": "UserR1",
            "first_post_id": "p-21",
            "first_post_author_user_id": "1",
            "first_post_author_username": "UserR1",
            "first_post_created_timestamp": 13,
        },
        {
            "thread_id": "t-3",
            "thread_title": "Thread 3",
            "thread_created_timestamp": 16,
            "thread_snippet": "",
            "thread_creator_username": "UserD1",
            "first_post_id": "p-31",
            "first_post_author_user_id": "2",
            "first_post_author_username": "UserD1",
            "first_post_created_timestamp": 16,
        },
        {
            "thread_id": "t-4",
            "thread_title": "Thread 4",
            "thread_created_timestamp": 50,
            "thread_snippet": "",
            "thread_creator_username": "UserR1",
            "first_post_id": "p-41",
            "first_post_author_user_id": "1",
            "first_post_author_username": "UserR1",
            "first_post_created_timestamp": 50,
        },
    ]
    sample_parent_posts: List[Context.ParentPost] = [
        {
            "post_id": "p-11",
            "posted_timestamp": 10,
            "post_title": "Post 11",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
        },
        {
            "post_id": "p-21",
            "posted_timestamp": 13,
            "post_title": "Post 21",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
        },
        {
            "post_id": "p-212",
            "posted_timestamp": 20,
            "post_title": "Post 212",
            "post_snippet": "",
            "author_user_id": "3",
            "author_username": "UserD2",
        },
        {
            "post_id": "p-32",
            "posted_timestamp": 21,
            "post_title": "Post 32",
            "post_snippet": "",
            "author_user_id": "3",
            "author_username": "UserD2",
        },
        {
            "post_id": "p-41",
            "posted_timestamp": 50,
            "post_title": "Post 41",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
        },
    ]
    sample_posts: List[NotifiablePost] = [
        {
            "post_id": "p-11",
            "posted_timestamp": 10,
            "post_title": "Post 11",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-1",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-111",
            "posted_timestamp": 30,
            "post_title": "Post 111",
            "post_snippet": "",
            "author_user_id": "2",
            "author_username": "UserD1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-1",
            "context_parent_post_id": "p-11",
        },
        {
            "post_id": "p-12",
            "posted_timestamp": 20,
            "post_title": "Post 12",
            "post_snippet": "",
            "author_user_id": "2",
            "author_username": "UserD1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-1",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-21",
            "posted_timestamp": 13,
            "post_title": "Post 21",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-2",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-211",
            "posted_timestamp": 17,
            "post_title": "Post 211",
            "post_snippet": "",
            "author_user_id": "2",
            "author_username": "UserD1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-2",
            "context_parent_post_id": "p-21",
        },
        {
            "post_id": "p-212",
            "posted_timestamp": 20,
            "post_title": "Post 212",
            "post_snippet": "",
            "author_user_id": "3",
            "author_username": "UserD2",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-2",
            "context_parent_post_id": "p-21",
        },
        {
            "post_id": "p-2121",
            "posted_timestamp": 23,
            "post_title": "Post 2121",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-2",
            "context_parent_post_id": "p-212",
        },
        {
            "post_id": "p-31",
            "posted_timestamp": 16,
            "post_title": "Post 31",
            "post_snippet": "",
            "author_user_id": "2",
            "author_username": "UserD1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-3",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-32",
            "posted_timestamp": 21,
            "post_title": "Post 32",
            "post_snippet": "",
            "author_user_id": "3",
            "author_username": "UserD2",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-3",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-321",
            "posted_timestamp": 31,
            "post_title": "Post 321",
            "post_snippet": "",
            "author_user_id": "2",
            "author_username": "UserD1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-3",
            "context_parent_post_id": "p-32",
        },
        {
            "post_id": "p-41",
            "posted_timestamp": 50,
            "post_title": "Post 41",
            "post_snippet": "",
            "author_user_id": "1",
            "author_username": "UserR1",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-4",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-411",
            "posted_timestamp": 60,
            "post_title": "Post 411",
            "post_snippet": "",
            "author_user_id": "3",
            "author_username": "UserD2",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-4",
            "context_parent_post_id": "p-41",
        },
        {
            "post_id": "p-42",
            "posted_timestamp": 65,
            "post_title": "Post 42",
            "post_snippet": "",
            "author_user_id": "3",
            "author_username": "UserD2",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-4",
            "context_parent_post_id": None,
        },
    ]
    sample_channel_log: List[ChannelLogDump] = [
        {
            "channel": "hourly",
            "start_timestamp": 30,
            "end_timestamp": 31,
            "notified_user_count": 2,
        },
        {
            "channel": "daily",
            "start_timestamp": 32,
            "end_timestamp": 33,
            "notified_user_count": 0,
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
    }
    db.store_user_configs(sample_user_configs)
    db.store_supported_wikis(sample_wikis)
    for thread in sample_threads:
        db.store_context_thread(thread)
    for parent_post in sample_parent_posts:
        db.store_context_parent_post(parent_post)
    for post in sample_posts:
        db.store_post(post)
    for channel_log in sample_channel_log:
        db.store_channel_log_dump(channel_log)
    db.store_activation_log_dump(sample_activation_log)
    return db


def titles(posts: Sequence[PostInfo]) -> Set[str]:
    """Get a set of post titles from a list of posts."""
    return set(p["title"] for p in posts)


@pytest.fixture(scope="class")
def new_posts_for_user(
    sample_database: BaseDatabaseDriver,
) -> List[PostInfo]:
    """Extract new posts for a single user from the sample database."""
    return sample_database.get_notifiable_posts_for_user("1", (0, 100))


@pytest.mark.needs_database
def test_counting(sample_database: BaseDatabaseDriver) -> None:
    """Test that the driver can count."""
    assert len(sample_database.get_supported_wikis()) == 1
    assert sample_database.count_user_configs() == 1


@pytest.mark.needs_database
def test_get_post_reply_even_if_ignored_thread(
    new_posts_for_user: List[PostInfo],
) -> None:
    """Test that post replies are returned even if the thread is ignored."""
    assert "Post 411" in titles(new_posts_for_user)


@pytest.mark.needs_database
def test_ignore_already_responded_post(
    new_posts_for_user: List[PostInfo],
) -> None:
    """Test that post replies are not returned if the user has already
    responded to them."""
    assert "Post 212" not in titles(new_posts_for_user)


@pytest.mark.needs_database
def test_ignore_own_post_in_thread(new_posts_for_user: List[PostInfo]) -> None:
    """Test that the user is not notified of their own posts to a thread."""
    assert titles(new_posts_for_user).isdisjoint(
        {"Post 11", "Post 21", "Post 2121", "Post 41"}
    )


@pytest.mark.needs_database
def test_get_replied_posts(new_posts_for_user: List[PostInfo]) -> None:
    """Test that the post replies are as expected."""
    assert titles(
        [
            p
            for p in new_posts_for_user
            if p["flag_user_started_thread"]
            or p["flag_user_subscribed_to_thread"]
        ]
    ) == {
        "Post 111",
        "Post 211",
        "Post 411",
        "Post 321",
    }


@pytest.mark.needs_database
def test_get_posts_in_threads(new_posts_for_user: List[PostInfo]) -> None:
    """Test that thread posts are as expected."""
    assert titles(
        [
            p
            for p in new_posts_for_user
            if p["flag_user_posted_parent"]
            or p["flag_user_subscribed_to_post"]
        ]
    ) == {"Post 12"}


@pytest.mark.needs_database
def test_respect_ignored_thread(new_posts_for_user: List[PostInfo]) -> None:
    """Test that posts in ignored threads do not appear as thread posts."""
    assert titles(new_posts_for_user).isdisjoint({"Post 41", "Post 42"})


@pytest.mark.needs_database
def test_initial_notified_timestamp(sample_database: MySqlDriver) -> None:
    """Test that the initial last notified timestamp for a user is set."""
    with sample_database.transaction() as cursor:

        def check_timestamp(n: int) -> None:
            cursor.execute(
                """
                SELECT notified_timestamp
                FROM user_config
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


@pytest.mark.needs_database
def test_get_notifiable_users(sample_database: MySqlDriver) -> None:
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
    sample_threads: List[Context.Thread] = [
        {
            "thread_id": "t-5",
            "thread_created_timestamp": 100,
            "thread_title": "Thread 5",
            "thread_snippet": "",
            "thread_creator_username": "T5U-Starter",
            "first_post_id": "p-51",
            "first_post_author_user_id": "53",
            "first_post_author_username": "T5U-Starter",
            "first_post_created_timestamp": 100,
        }
    ]
    sample_posts: List[NotifiablePost] = [
        {
            "post_id": "p-51",
            "posted_timestamp": 100,
            "post_title": "Post 51",
            "post_snippet": "",
            "author_user_id": "53",
            "author_username": "T5U-Starter",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-52",
            "posted_timestamp": 101,
            "post_title": "Post 52",
            "post_snippet": "",
            "author_user_id": "55",
            "author_username": "T5U-Poster",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-521",
            "posted_timestamp": 102,
            "post_title": "Post 521",
            "post_snippet": "",
            "author_user_id": "52",
            "author_username": "T5U-Lonely",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": "p-52",
        },
        {
            "post_id": "p-53",
            "posted_timestamp": 103,
            "post_title": "Post 53",
            "post_snippet": "",
            "author_user_id": "54",
            "author_username": "T5U-SelfRep",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-531",
            "posted_timestamp": 104,
            "post_title": "Post 531",
            "post_snippet": "",
            "author_user_id": "54",
            "author_username": "T5U-SelfRep",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": "p-53",
        },
        {
            "post_id": "p-54",
            "posted_timestamp": 106,
            "post_title": "Post 54",
            "post_snippet": "",
            "author_user_id": "56",
            "author_username": "T5U-UnsubPost",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-541",
            "posted_timestamp": 105,
            "post_title": "Post 541",
            "post_snippet": "",
            "author_user_id": "52",
            "author_username": "T5U-Lonely",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": "p-54",
        },
        {
            "post_id": "p-55",
            "posted_timestamp": 106,
            "post_title": "Post 55",
            "post_snippet": "",
            "author_user_id": "50",
            "author_username": "T5U-Unsub",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-551",
            "posted_timestamp": 107,
            "post_title": "Post 551",
            "post_snippet": "",
            "author_user_id": "52",
            "author_username": "T5U-Lonely",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": "p-55",
        },
        {
            "post_id": "p-56",
            "posted_timestamp": 108,
            "post_title": "Post 56",
            "post_snippet": "",
            "author_user_id": "57",
            "author_username": "T5U-PrevNotif",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": None,
        },
        {
            "post_id": "p-561",
            "posted_timestamp": 109,
            "post_title": "Post 561",
            "post_snippet": "",
            "author_user_id": "52",
            "author_username": "T5U-Lonely",
            "context_wiki_id": "my-wiki",
            "context_forum_category_id": None,
            "context_thread_id": "t-5",
            "context_parent_post_id": "p-56",
        },
    ]

    for post in sample_posts:
        if not any(
            post["author_user_id"] == user["user_id"]
            and post["author_username"] == user["username"]
            for user in sample_user_configs
        ):
            raise RuntimeError("Bad name")

    # verify=verify_post_author_id_matches_username
    sample_database.store_user_configs(
        sample_user_configs, overwrite_existing=False
    )
    for thread in sample_threads:
        sample_database.store_context_thread(thread)
    for post in sample_posts:
        sample_database.store_post(post)

    assert set(sample_database.get_notifiable_users("hourly", 0)) == {
        "1",  # UserR1 from base sample DB
        "51",  # T5U-!P-Sub
        "53",  # T5U-Starter
        "55",  # T5U-Poster
    }

    with sample_database.transaction() as cursor:
        cursor.execute("DROP TABLE post_with_context")

    assert set(sample_database.get_notifiable_users("hourly", 99)) == {
        "51",  # T5U-!P-Sub
        "53",  # T5U-Starter
        "55",  # T5U-Poster
    }
