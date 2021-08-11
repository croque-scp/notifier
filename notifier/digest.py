import re
from collections import defaultdict
from functools import lru_cache
from itertools import groupby
from re import Match
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    cast,
)

import tomlkit
from emoji import emojize

from notifier.types import (
    CachedUserConfig,
    DeliveryMethod,
    IsSecure,
    NewPostsInfo,
    PostInfo,
    PostReplyInfo,
    ThreadPostInfo,
)


def make_thread_url(
    wiki_id: str,
    wiki_secure: IsSecure,
    thread_id: str,
    post_id: Optional[str] = None,
) -> str:
    """Constructs a URL pointing to a thread, or a specific post in a
    thread."""
    return "http{}://{}.wikidot.com/forum/{}{}".format(
        "s" if wiki_secure else "",
        wiki_id,
        thread_id,
        f"/#{post_id}" if post_id else "",
    )


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
        outro = lexicon["outro"].format(unsubscribe=lexicon["unsubscribe"])
        body = lexicon["body"].format(
            intro=intro,
            wikis="\n".join(make_wikis_digest(posts, lexicon)),
            footer=lexicon["footer"],
            outro=outro,
        )
        # Pluralise
        body = pluralise(body)
        # Add emojis
        body = emojize(body)
        return subject, body


def make_wikis_digest(new_posts: NewPostsInfo, lexicon: dict) -> List[str]:
    """Makes the notification list."""
    thread_posts = new_posts["thread_posts"]
    post_replies = new_posts["post_replies"]
    digests: List[str] = []
    # Group posts by their wiki ID
    grouped_posts = group_posts(thread_posts, "wiki_id")
    grouped_replies = group_posts(post_replies, "wiki_id")
    # Iterate wikis by notification count
    for wiki_id in frequent_ids(grouped_posts, grouped_replies):
        posts = cast(List[ThreadPostInfo], grouped_posts[wiki_id])
        replies = cast(List[PostReplyInfo], grouped_replies[wiki_id])
        first_post = (posts + cast(List[PostInfo], replies))[0]
        digests.append(
            lexicon["wiki"].format(
                wiki_name=first_post["wiki_name"],
                categories="\n".join(
                    make_categories_digest(posts, replies, lexicon)
                ),
            )
        )
    return digests


def make_categories_digest(
    thread_posts: Sequence[ThreadPostInfo],
    post_replies: Sequence[PostReplyInfo],
    lexicon: dict,
) -> List[str]:
    """Makes the notification list for categories in a given wiki."""
    digests: List[str] = []
    grouped_posts = group_posts(thread_posts, "category_id")
    grouped_replies = group_posts(post_replies, "category_id")
    # Sort categories by notification count
    for category_id in frequent_ids(grouped_posts, grouped_replies):
        posts = cast(List[ThreadPostInfo], grouped_posts[category_id])
        replies = cast(List[PostReplyInfo], grouped_replies[category_id])
        first_post = (posts + cast(List[PostInfo], replies))[0]
        threads = make_threads_digest(posts, replies, lexicon)
        digests.append(
            lexicon["category"].format(
                category_name=first_post["category_name"],
                summary=lexicon["summary"].format(
                    notification_count=len(posts) + len(replies),
                    thread_count=len(threads),
                ),
                threads=threads,
            )
        )
    return digests


def make_threads_digest(
    thread_posts: Sequence[ThreadPostInfo],
    post_replies: Sequence[PostReplyInfo],
    lexicon: dict,
) -> List[str]:
    """Makes the notification list for threads in a given category."""
    digests: List[str] = []
    # I want to group the posts in both lists by thread ID and then
    # iterate over them both, but can only guarantee that at least one list
    # contains any given thread ID.
    # Create a defaultdict keyed by thread ID with an empty iterable
    # default value for both lists
    grouped_posts = group_posts(thread_posts, "thread_id")
    grouped_replies = group_posts(post_replies, "thread_id")
    # Iterate over the thread IDs sorted by notification count
    for thread_id in frequent_ids(grouped_posts, grouped_replies):
        posts = cast(List[ThreadPostInfo], grouped_posts[thread_id])
        replies = cast(List[PostReplyInfo], grouped_replies[thread_id])
        # For each thread, there is necessarily at least one post in either
        # the thread posts or the post replies
        posts_section = ""
        if len(posts) > 0:
            posts_section = lexicon["posts_section"].format(
                posts="\n".join(make_posts_digest(posts, lexicon))
            )
        replies_section = ""
        if len(replies) > 0:
            replies_section = lexicon["replies_section"].format(
                posts_replied_to="\n".join(
                    make_post_replies_digest(replies, lexicon)
                )
            )
        first_post = (posts + cast(List[PostInfo], replies))[0]
        digests.append(
            lexicon["thread"].format(
                thread_opener=lexicon["thread_opener"],
                thread_url=make_thread_url(
                    first_post["wiki_id"],
                    first_post["wiki_secure"],
                    first_post["thread_id"],
                ),
                thread_title=first_post["thread_title"],
                thread_has_creator=int(bool(first_post["thread_creator"])),
                thread_creator=first_post["thread_creator"],
                date=lexicon["date"].format(first_post["thread_timestamp"]),
                replies_section=replies_section,
                posts_rection=posts_section,
            )
        )
    return digests


def make_post_replies_digest(
    post_replies: Iterable[PostReplyInfo], lexicon: dict
) -> List[str]:
    """Makes the notification list for replies in a given thread."""
    digests: List[str] = []
    # Groups replies by their parent post, provided that they have already
    # been sorted by their parent post ID
    grouped_replies = groupby(
        post_replies, key=lambda reply: reply["parent_post_id"]
    )
    for parent_post_id, replies_group in grouped_replies:
        replies = list(replies_group)
        posts = make_posts_digest(replies, lexicon)
        digests.append(
            lexicon["post_replied_to"].format(
                post_replies_opener=lexicon["post_replies_opener"],
                post_url=make_thread_url(
                    replies[0]["wiki_id"],
                    replies[0]["wiki_secure"],
                    replies[0]["thread_id"],
                    parent_post_id,
                ),
                post_title=replies[0]["parent_title"],
                date=lexicon["date"].format(
                    replies[0]["parent_posted_timestamp"]
                ),
                posts_section=lexicon["posts_section"].format(
                    posts="\n".join(posts),
                ),
            )
        )
    return digests


def make_posts_digest(posts: Iterable[PostInfo], lexicon: dict) -> List[str]:
    """Makes the notification list for new posts."""
    return [make_post_digest(post, lexicon) for post in posts]


def make_post_digest(post: PostInfo, lexicon: dict) -> str:
    """Makes a notification for a single post."""
    return lexicon["post"].format(
        post_url=make_thread_url(
            post["wiki_id"], post["wiki_secure"], post["thread_id"], post["id"]
        ),
        post_title=post["title"],
        post_author=post["username"],
        date=lexicon["date"].format(post["posted_timestamp"]),
        snippet=post["snippet"],
    )


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

    Substrings of the form `plural(N|X|Y)` with are replaced with X if N is
    an integer and is 1, and Y otherwise.
    """
    plural = re.compile(r"plural\(([0-9]+)\|(.*?)\|(.*?)\)")
    return plural.sub(make_plural, string)


def make_plural(match: Match) -> str:
    """Returns the single or plural result from a pluralisation match."""
    amount, single, multiple = match.groups()
    try:
        amount = int(amount)
    except ValueError:
        return multiple
    if amount > 1:
        return multiple
    return single


def group_posts(
    posts: Iterable[PostInfo], grouping_key: str
) -> DefaultDict[str, List[PostInfo]]:
    """Group a set of posts by the given grouping key.

    Should be used on lists of posts to group them by some criteria, e.g.
    by their thread ID. Must only be used on lists of posts that have
    already been sorted by the grouping key; generally we assume that the
    decached data was sorted on its way out of the database.

    Returns a defaultdict. The keys of the dict are instances of the
    grouping key, and the values are a list of posts for each grouping key.
    Default values are the empty list.
    """
    return defaultdict(
        cast(Callable[[], Any], list),
        {
            cast(str, id): list(posts)
            for id, posts in groupby(
                posts, key=lambda post: post.get(grouping_key, None)
            )
        },
    )


def frequent_ids(*post_groups: DefaultDict[str, List[PostInfo]]) -> List[str]:
    """From a set of dicts containing grouped posts, return the keys from
    all provided dicts sorted by the number of posts that each key maps to,
    in descending order."""
    return sorted(
        set().union(*cast(Iterable, [group.keys() for group in post_groups])),
        key=lambda id: sum(len(group[id]) for group in post_groups),
        reverse=True,
    )
