from pathlib import Path
from typing import List

import pytest

from notifier.digest import (
    Digester,
    finalise_digest,
    make_wikis_digest,
    pluralise,
    process_long_lexicon_strings,
    process_long_string,
)
from notifier.formatter import convert_syntax
from notifier.types import CachedUserConfig, PostInfo

fake_user_config: CachedUserConfig = {  # TODO Subscriptions
    "user_id": "1000",
    "username": "Me",
    "frequency": "hourly",
    "language": "en",
    "delivery": "pm",
    "last_notified_timestamp": 0,
    "tags": "",
    "manual_subs": [],
}


def fake_posts() -> List[PostInfo]:
    """Create a set of posts as would be returned from the cache."""
    thread_posts: List[PostInfo] = [
        {
            "id": f"post-{post_index}",
            "posted_timestamp": post_timestamp,
            "title": f"Post {post_index}",
            "snippet": "Contents...",
            "username": "AnotherUser",
            "wiki_id": "my-wiki",
            "wiki_name": "My Wiki",
            "wiki_secure": 1,
            "category_id": None,
            "category_name": None,
            "thread_id": f"t-{thread_index}",
            "thread_timestamp": thread_index * 10,
            "thread_title": f"Post {thread_index}",
            "thread_creator": "AnotherUser",
            "parent_post_id": None,
            "parent_posted_timestamp": None,
            "parent_title": None,
            "parent_username": None,
            "flag_user_subscribed_to_thread": True,
            "flag_user_subscribed_to_post": False,
            "flag_user_started_thread": False,
            "flag_user_posted_parent": False,
        }
        for thread_index in range(1, 2 + 1)
        for post_index in range(1, 3 + 1)
        for post_timestamp in [thread_index * 10 + post_index]
        if post_timestamp >= fake_user_config["last_notified_timestamp"]
    ]
    thread_replies: List[PostInfo] = [
        {
            "id": f"post-{post_index}",
            "posted_timestamp": post_timestamp,
            "title": f"Post {post_index}",
            "snippet": "Response...",
            "username": "AnotherUser",
            "wiki_id": "my-wiki",
            "wiki_name": "My Wiki",
            "wiki_secure": 1,
            "category_id": None,
            "category_name": None,
            "thread_id": f"t-{thread_index}",
            "thread_timestamp": thread_index * 10,
            "thread_title": f"Post {thread_index}",
            "thread_creator": "AnotherUser",
            "parent_post_id": f"post-{parent_index}",
            "parent_posted_timestamp": parent_index * 10,
            "parent_title": f"Post {parent_index}",
            "parent_username": "Me",
            "flag_user_subscribed_to_thread": False,
            "flag_user_subscribed_to_post": True,
            "flag_user_started_thread": False,
            "flag_user_posted_parent": False,
        }
        for thread_index in range(1, 2 + 1)
        for parent_index in range(1, 2 + 1)
        for post_index in [
            (parent_index * 10) + post_index for post_index in range(1, 2 + 1)
        ]
        for post_timestamp in [(thread_index + parent_index) * 10 + post_index]
        if post_timestamp >= fake_user_config["last_notified_timestamp"]
    ]
    return thread_posts + thread_replies


def test_long_string_processor() -> None:
    """Test the algorithm for removing newlines from long strings."""
    p = process_long_string
    tests = [
        ("test", "test"),
        ("|test", "test"),
        ("|\ntest\n", "test"),
        ("|\n1\n2\n", "1 2"),
        ("|\n1\n\n2\n", "1\n\n2"),
        ("|\n1<>2\n", "1\n2"),
    ]
    for i, o in tests:
        assert p(i) == o


def test_lexicon_processor() -> None:
    """Test processing long strings in a lexicon."""
    assert process_long_lexicon_strings({"1": "test", "2": "|\ntest\n"}) == {
        "1": "test",
        "2": "test",
    }


def test_pluralise() -> None:
    """Test the pluralisation string replacement algorithm."""
    assert pluralise("plural(0|s|m)", "en") == "m"
    assert pluralise("plural(1|s|m)", "en") == "s"
    assert pluralise("plural(2|s|m)", "en") == "m"
    with pytest.raises(ValueError):
        pluralise("plural(X|s|m)", "en")
    assert pluralise("aaaaaplural(1|s|m)aaaaa", "en") == "aaaaasaaaaa"
    assert (
        pluralise("plural(1000|s|m)plural(1|y god|olasses)", "en") == "my god"
    )

    # Polish
    # 1 - singular, 2-4 - paucal, 0/5+ - multiple
    assert pluralise("plural(1|single|paucal|multiple)", "pl") == "single"
    assert pluralise("plural(2|single|paucal|multiple)", "pl") == "paucal"
    assert pluralise("plural(22|single|paucal|multiple)", "pl") == "paucal"
    assert pluralise("plural(102|single|paucal|multiple)", "pl") == "paucal"
    assert pluralise("plural(5|single|paucal|multiple)", "pl") == "multiple"
    assert pluralise("plural(0|single|paucal|multiple)", "pl") == "multiple"
    assert pluralise("plural(112|single|paucal|multiple)", "pl") == "multiple"


def test_fake_digest() -> None:
    """Construct a digest from fake data and compare it to the expected
    output."""
    digester = Digester(str(Path.cwd() / "config" / "lang.toml"))
    lexicon = digester.make_lexicon(fake_user_config["language"])
    digest = "\n".join(make_wikis_digest(fake_posts(), lexicon))
    print(digest)
    print(digest[:25].replace("\n", "\\n"))

    # Would be prohibitively difficult to test an exact match for the digest - manual inspection should be sufficient. But I can check that it does produce something and that it has the expected number of notifications:
    assert digest.startswith("++ My Wiki\n\n+++ Other\n\n14")
    assert digest.count(lexicon["thread_opener"]) == 2
    assert digest.count(lexicon["post_replies_opener"]) == 4
    assert digest.count("Contents...") == 6
    assert digest.count("Response...") == 8

    # Print an email output for review
    print(convert_syntax(finalise_digest(digest, "en"), "email"))


def test_full_interpolation_en() -> None:
    """Verify that there's no leftover interpolation in the English digest."""

    digester = Digester(str(Path.cwd() / "config" / "lang.toml"))
    languages = set(digester.lexicons.keys())
    languages.remove("base")

    for delivery in ("email", "pm"):
        digest = digester.for_user(
            {
                **fake_user_config,
                "language": "en",
                "delivery": delivery,
            },
            fake_posts(),
        )
        assert "{" not in digest


def test_full_interpolation_all_languages() -> None:
    """Verify that there's no leftover interpolation in any language's digest."""

    digester = Digester(str(Path.cwd() / "config" / "lang.toml"))
    languages = set(digester.lexicons.keys())
    languages.remove("base")

    for language in languages:
        for delivery in ("email", "pm"):
            print(language, delivery)
            subject, body = digester.for_user(
                {
                    **fake_user_config,
                    "language": language,
                    "delivery": delivery,
                },
                fake_posts(),
            )
            # print(subject, body)
            assert "{" not in body, language
            assert "plural(" not in body, language
