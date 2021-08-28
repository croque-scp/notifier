from pathlib import Path

import pytest

from notifier.digest import (
    Digester,
    make_wikis_digest,
    pluralise,
    process_long_strings,
)
from notifier.formatter import convert_syntax
from notifier.notify import apply_overrides, override_applies_to_post
from notifier.types import (
    CachedUserConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
)


@pytest.fixture(scope="module")
def fake_user() -> CachedUserConfig:
    """Create a fake user config."""
    return {  # TODO Subscriptions and auto subscriptions
        "user_id": "1000",
        "username": "Me",
        "frequency": "hourly",
        "language": "en",
        "delivery": "pm",
        "last_notified_timestamp": 0,
        "manual_subs": [],
        "auto_subs": [],
    }


@pytest.fixture(scope="module")
def fake_posts(fake_user: CachedUserConfig) -> NewPostsInfo:
    """Create a set of posts as would be returned from the cache."""
    return {
        "thread_posts": [
            {
                "id": f"post-{post_index}",
                "title": f"Post {post_index}",
                "username": "AnotherUser",
                "posted_timestamp": post_timestamp,
                "snippet": "Contents...",
                "thread_id": f"t-{thread_index}",
                "thread_title": f"Post {thread_index}",
                "thread_creator": "AnotherUser",
                "thread_timestamp": thread_index * 10,
                "wiki_id": "my-wiki",
                "wiki_name": "My Wiki",
                "wiki_secure": 1,
                "category_id": None,
                "category_name": None,
            }
            for thread_index in range(1, 2 + 1)
            for post_index in range(1, 3 + 1)
            for post_timestamp in [thread_index * 10 + post_index]
            if post_timestamp >= fake_user["last_notified_timestamp"]
        ],
        "post_replies": [
            {
                "id": f"post-{post_index}",
                "title": f"Post {post_index}",
                "username": "AnotherUser",
                "posted_timestamp": post_timestamp,
                "snippet": "Response...",
                "thread_id": f"t-{thread_index}",
                "thread_title": f"Post {thread_index}",
                "thread_creator": "AnotherUser",
                "thread_timestamp": thread_index * 10,
                "wiki_id": "my-wiki",
                "wiki_name": "My Wiki",
                "wiki_secure": 1,
                "category_id": None,
                "category_name": None,
                "parent_post_id": f"post-{parent_index}",
                "parent_title": f"Post {parent_index}",
                "parent_username": "Me",
                "parent_posted_timestamp": parent_index * 10,
            }
            for thread_index in range(1, 2 + 1)
            for parent_index in range(1, 2 + 1)
            for post_index in [
                (parent_index * 10) + post_index
                for post_index in range(1, 2 + 1)
            ]
            for post_timestamp in [
                (thread_index + parent_index) * 10 + post_index
            ]
            if post_timestamp >= fake_user["last_notified_timestamp"]
        ],
    }


def test_long_string_processor():
    """Test the algorithm for removing newlines from long strings."""
    p = process_long_strings
    tests = [
        ("test", "test"),
        ("|test", "test"),
        ("|\ntest\n", "test"),
        ("|\n1\n2\n", "1 2"),
        ("|\n1\n\n2\n", "1\n\n2"),
        ("|\n1<>2\n", "1\n2"),
        ({1: "test", 2: "|\ntest\n"}, {1: "test", 2: "test"}),
    ]
    for i, o in tests:
        assert p(i) == o


def test_pluralise():
    """Test the pluralisation string replacement algorithm."""
    assert pluralise("plural(0|s|m)") == "m"
    assert pluralise("plural(1|s|m)") == "s"
    assert pluralise("plural(2|s|m)") == "m"
    assert pluralise("plural(X|s|m)") == "m"
    assert pluralise("aaaaaplural(1|s|m)aaaaa") == "aaaaasaaaaa"
    assert pluralise("plural(X|s|m)plural(1|y god|olasses)") == "my god"


def test_fake_digest(fake_user: CachedUserConfig, fake_posts: NewPostsInfo):
    """Construct a digest from fake data and compare it to the expected
    output."""
    digester = Digester(str(Path.cwd() / "notifier" / "lang.toml"))
    lexicon = digester.make_lexicon(fake_user["language"])
    digest = "\n".join(make_wikis_digest(fake_posts, lexicon))
    print(digest)
    print(digest[:25].replace("\n", "\\n"))
    # Would be prohibitively difficult to test an exact match for the
    # digest - manual inspection should be sufficient. But I can check that
    # it does produce something and that it has the expected number of
    # notifications:
    assert digest.startswith("++ My Wiki\n\n+++ Other\n\n14")
    assert digest.count(lexicon["thread_opener"]) == 2
    assert digest.count(lexicon["post_replies_opener"]) == 4
    assert digest.count("Contents...") == 6
    assert digest.count("Response...") == 8
    print(convert_syntax(digest, "email"))


def test_overrides(fake_posts: NewPostsInfo):
    """Check that application of overrides to mute notifications globally
    works."""
    overrides: GlobalOverridesConfig = {
        "my-wiki": [
            {"action": "mute", "thread_id_is": "t-1"},
            {"action": "mute_thread", "thread_title_matches": "Post 2"},
        ]
    }
    assert override_applies_to_post(
        fake_posts["thread_posts"][0], overrides["my-wiki"][0]
    )
    apply_overrides(fake_posts, overrides)
    assert (
        len(
            [
                reply
                for reply in fake_posts["post_replies"]
                if reply["thread_id"] == "t-1"
            ]
        )
        == 0
    )
    assert (
        len(
            [
                reply
                for reply in fake_posts["post_replies"]
                if reply["thread_title"].startswith("Post 2")
            ]
        )
        != 0
    )
    assert (
        len(
            [
                post
                for post in fake_posts["thread_posts"]
                if post["thread_title"].startswith("Post 2")
            ]
        )
        == 0
    )
