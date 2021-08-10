import re
from functools import lru_cache
from re import Match
from typing import Dict, Tuple, TypeVar

import tomlkit
from emoji import emojize

from notifier.types import CachedUserConfig, DeliveryMethod, NewPostsInfo


class Digester:
    """Constructs notification digests."""

    def __init__(self, lang_path: str):
        # Read the strings from the lexicon file
        with open(lang_path, "r") as lang_file:
            self.lexicon = dict(tomlkit.parse(lang_file.read()))
        # Process long strings (marked with a leading pipe)
        self.lexicon = process_long_strings(self.lexicon)

    @lru_cache(maxsize=None)
    def make_lexicon(self, lang: str, method: DeliveryMethod):
        """Constructs a subset of the full lexicon for a given language and
        delivery method.

        These lexicons are cached per language and method, which will be
        necessarily cleared on construction of a new Digester.
        """
        # Later keys in the lexicon will override previous ones - e.g. for
        # a non-en language, its keys should override all of en's, but in
        # case they don't, en's are used as a fallback.
        lexicon = {
            **self.lexicon["base"],
            **self.lexicon["base"][method],
            **self.lexicon["en"],
            **self.lexicon["en"][method],
            **self.lexicon[lang],
            **self.lexicon[lang][method],
        }
        return lexicon

    def for_user(  # pylint: disable=too-many-locals
        self, user: CachedUserConfig, posts: NewPostsInfo
    ) -> Tuple[str, str]:
        """Compile a notification digest for a user.

        Returns a tuple of the message subject and the digest body.
        """
        # Make the lexicon for this user's settings
        lexicon = self.make_lexicon(user["language"], user["delivery"])
        # Get some stats for the message
        sub_count = None
        manual_sub_count = None
        auto_thread_sub_count = None
        auto_post_sub_count = None
        total_notification_count = None
        total_notified_thread_count = None
        wiki_count = None
        # Construct the message
        subject = lexicon["subject"].format(
            post_count=total_notification_count
        )
        frequency = {
            "hourly": lexicon["frequency_hourly"],
            "daily": lexicon["frequency_daily"],
            "weekly": lexicon["frequency_weekly"],
            "monthly": lexicon["frequency_monthly"],
        }[user["frequency"]]
        intro = lexicon["intro"].format(
            frequency=frequency,
            site=lexicon["site"],
            sub_count=sub_count,
            manual_sub_count=manual_sub_count,
            your_config=lexicon["your_config"],
            auto_thread_sub_count=auto_thread_sub_count,
            auto_post_sub_count=auto_post_sub_count,
        )
        main_summary = lexicon["main_summary"].format(
            summary=lexicon["summary"].format(
                notification_count=total_notification_count,
                thread_count=total_notified_thread_count,
            ),
            wiki_count=wiki_count,
        )
        wikis = self.make_wiki_list(posts, lexicon)
        outro = lexicon["outro"].format(unsubscribe=lexicon["unsubscribe"])
        body = lexicon["body"].format(
            intro=intro,
            main_summary=main_summary,
            wikis=wikis,
            footer=lexicon["footer"],
            outro=outro,
        )
        # Pluralise
        body = pluralise(body)
        # Add emojis
        body = emojize(body)
        return subject, body

    def make_wiki_list(self, posts: NewPostsInfo, lexicon: dict) -> str:
        """Makes the notification list."""
        thread_posts = posts["thread_posts"]
        post_replies = posts["post_replies"]
        # Get the list of wikis
        wiki_ids = list(
            set(post["wiki_id"] for post in thread_posts).union(
                set(reply["wiki_id"] for reply in post_replies)
            )
        )
        for wiki_id in wiki_ids:
            thread_posts = [
                post for post in thread_posts if post["wiki_id"] == wiki_id
            ]
            post_replies = [
                reply for reply in post_replies if reply["wiki_id"] == wiki_id
            ]


lex_or_string = TypeVar("lex_or_string", str, Dict)


def process_long_strings(lexicon: lex_or_string) -> lex_or_string:
    """Process long strings in the main lexicon.

    Strings marked for concatenation are indicated with a leading pipe.
    """
    if isinstance(lexicon, str):
        if lexicon.startswith("|"):
            lexicon = (
                # Remove leading/trailing newlines and the pipe
                lexicon.strip("|\n")
                # Save double newlines for later
                .replace("\n\n", "<<>>")
                # Remove single newlines
                .replace("\n", " ")
                # Recover double newlines
                .replace("<<>>", "\n\n")
                # Insert manual single newlines
                .replace("<>", "\n")
            )
        return lexicon
    return {key: process_long_strings(value) for key, value in lexicon.items()}


def pluralise(string: str) -> str:
    """Pluralises a string.

    Substrings of the form `plural(N|X|Y)` with int N are replaced with X
    if N is 1 and Y otherwise.
    """
    plural = re.compile(r"plural\(([0-9]+)\|(.*)\|(.*)\)")
    return plural.sub(make_plural, string)


def make_plural(match: Match):
    """Returns the single or plural result from a pluralisation match."""
    amount, single, multiple = match.groups()
    try:
        amount = int(amount)
    except ValueError:
        return multiple
    if amount > 1:
        return multiple
    return single
