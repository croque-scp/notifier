import re
from collections import defaultdict
from functools import lru_cache
from itertools import groupby
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    cast,
    Match,
)

import tomlkit
from emoji import emojize

from notifier.formatter import convert_syntax
from notifier.types import CachedUserConfig, IsSecure, PostInfo

Lexicon = Dict[str, str]
Lexicons = Dict[str, Lexicon]


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
        # Read the strings from the lang file into a lexicon
        with open(lang_path, "r", encoding="utf-8") as lang_file:
            self.lexicons = cast(
                Lexicons, dict(tomlkit.parse(lang_file.read()))
            )

    @lru_cache(maxsize=1)
    def make_lexicon(self, lang: str) -> Lexicon:
        """Constructs a subset of the full lexicon for a given language."""
        # Later keys in the lexicon will override previous ones - e.g. for
        # a non-en language, its keys should override all of en's, but in
        # case they don't, en's are used as a fallback.
        lexicon = {
            **self.lexicons.get("base", {}),
            **self.lexicons.get("en", {}),
            **self.lexicons.get(lang, {}),
        }
        # Process long strings (marked with a leading pipe)
        lexicon = process_long_lexicon_strings(lexicon)
        return lexicon

    def for_user(
        self, user: CachedUserConfig, posts: Sequence[PostInfo]
    ) -> Tuple[str, str]:
        """Compile a notification digest for a user.

        Returns a tuple of message subject and the digest body.
        """
        # Make the lexicon for this user's settings
        lexicon = self.make_lexicon(user["language"])
        # Get some stats for the message
        manual_sub_count = len(
            [sub for sub in user["manual_subs"] if sub["sub"] == 1]
        )
        total_notification_count = len(posts)
        # Construct the message
        subject = lexicon["subject"].format(
            post_count=total_notification_count
        )
        frequency = {
            "hourly": lexicon["frequency_hourly"],
            "8hourly": lexicon["frequency_8hourly"],
            "daily": lexicon["frequency_daily"],
            "weekly": lexicon["frequency_weekly"],
            "monthly": lexicon["frequency_monthly"],
            "test": lexicon["frequency_test"],
        }.get(user["frequency"], "undefined")
        intro = lexicon["intro"].format(
            frequency=frequency,
            link_site=lexicon["link_site"],
            manual_sub_count=manual_sub_count,
            link_your_config=lexicon["link_your_config"].format(
                link_site=lexicon["link_site"]
            ),
            link_info_learning=lexicon["link_info_learning"].format(
                link_site=lexicon["link_site"]
            ),
            link_info_automatic=lexicon["link_info_automatic"].format(
                link_site=lexicon["link_site"]
            ),
        )
        outro = lexicon["outro"].format(
            unsub_footer=lexicon["unsub_footer"].format(
                link_unsubscribe=lexicon["link_unsubscribe"].format(
                    link_site=lexicon["link_site"]
                )
            )
        )
        body = lexicon["body"].format(
            intro=intro,
            wikis="\n".join(make_wikis_digest(posts, lexicon)),
            outro=outro,
        )
        subject = pluralise(subject)
        body = finalise_digest(body)
        body = convert_syntax(body, user["delivery"])
        return subject, body


def make_wikis_digest(
    posts: Sequence[PostInfo], lexicon: Lexicon
) -> List[str]:
    """Makes the notification list for wikis."""
    digests: List[str] = []
    # Group posts by their wiki ID
    grouped_posts = group_posts(posts, "wki_id")
    # Iterate wikis by notification count
    for wiki_id in frequent_ids(grouped_posts):
        wiki_posts = grouped_posts[wiki_id]
        digests.append(
            lexicon["wiki"].format(
                wiki_name=wiki_posts[0]["wiki_name"],
                categories="\n".join(
                    make_categories_digest(wiki_posts, lexicon)
                ),
            )
        )
    return digests


def make_categories_digest(
    posts: Sequence[PostInfo], lexicon: Lexicon
) -> List[str]:
    """Makes the notification list for categories in a given wiki."""
    digests: List[str] = []
    grouped_posts = group_posts(posts, "category_id")
    # Sort categories by notification count
    for category_id in frequent_ids(grouped_posts):
        category_posts = grouped_posts[category_id]
        threads = make_threads_digest(posts, lexicon)
        digests.append(
            lexicon["category"].format(
                category_name=category_posts[0].get("category_name")
                or lexicon["unknown_category_name"],
                summary=lexicon["summary"].format(
                    notification_count=len(category_posts),
                    thread_count=len(threads),
                ),
                threads="\n".join(threads),
            )
        )
    return digests


def make_threads_digest(
    posts: Sequence[PostInfo],
    lexicon: Lexicon,
) -> List[str]:
    """Makes the notification list for threads in a given category."""
    digests: List[str] = []
    # Split posts in the thread by whether it's a thread reply or a post reply
    # Either list (but not both) could be empty
    thread_posts: List[PostInfo] = []
    post_replies: List[PostInfo] = []
    for post in posts:
        (thread_posts, post_replies)[
            post["parent_post_id"] is not None
        ].append(post)
    # I want to group the posts in both lists by thread ID and then
    # iterate over them both, but can only guarantee that at least one list
    # contains any given thread ID.
    grouped_posts = group_posts(thread_posts, "thread_id")
    grouped_replies = group_posts(post_replies, "thread_id")
    # Iterate over the thread IDs sorted by notification count
    for thread_id in frequent_ids(grouped_posts, grouped_replies):
        posts = grouped_posts[thread_id]
        replies = grouped_replies[thread_id]
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
        first_post = (posts + replies)[0]
        digests.append(
            lexicon["thread"].format(
                thread_opener=lexicon["thread_opener"],
                thread_url=make_thread_url(
                    first_post["wiki_id"],
                    first_post["wiki_secure"],
                    first_post["thread_id"],
                ),
                thread_title=(
                    first_post["thread_title"]
                    or lexicon["untitled_post_title"]
                )
                .replace("[", "(")
                .replace("]", ")"),
                thread_has_creator=int(bool(first_post["thread_creator"])),
                thread_creator=first_post["thread_creator"],
                date=lexicon["date"].format(
                    timestamp=first_post["thread_timestamp"]
                ),
                replies_section=replies_section,
                posts_section=posts_section,
            )
        )
    return digests


def make_post_replies_digest(
    post_replies: Sequence[PostInfo], lexicon: Lexicon
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
                post_title=(
                    replies[0]["parent_title"]
                    or lexicon["untitled_post_title"]
                )
                .replace("[", "(")
                .replace("]", ")"),
                date=lexicon["date"].format(
                    timestamp=replies[0]["parent_posted_timestamp"]
                ),
                posts_section=lexicon["posts_section"].format(
                    posts="\n".join(posts),
                ),
            )
        )
    return digests


def make_posts_digest(
    posts: Iterable[PostInfo], lexicon: Lexicon
) -> List[str]:
    """Makes the notification list for new posts."""
    return [make_post_digest(post, lexicon) for post in posts]


def make_post_digest(post: PostInfo, lexicon: Lexicon) -> str:
    """Makes a notification for a single post."""
    return lexicon["post"].format(
        post_url=make_thread_url(
            post["wiki_id"], post["wiki_secure"], post["thread_id"], post["id"]
        ),
        post_title=(post["title"] or lexicon["untitled_post_title"])
        .replace("[", "(")
        .replace("]", ")"),
        post_author=post["username"],
        date=lexicon["date"].format(timestamp=post["posted_timestamp"]),
        snippet=post["snippet"].replace("\n", " "),
    )


def process_long_lexicon_strings(lexicon: Lexicon) -> Lexicon:
    """Process long strings in the given lexicon."""
    return {
        key: process_long_string(string) for key, string in lexicon.items()
    }


def process_long_string(string: str) -> str:
    """Process a long string.

    Strings marked for concatenation in the lexicon are indicated with a
    leading pipe.
    """
    if string.startswith("|"):
        string = (
            # Remove the pipe
            string.lstrip("|\n")
            # Save double newlines for later
            .replace("\n\n", "<<>>")
            # Remove single newlines
            .replace("\n", " ")
            # Recover double newlines
            .replace("<<>>", "\n\n")
            # Insert manual single newlines
            .replace("<>", "\n")
        )
    return string.strip()


def pluralise(string: str) -> str:
    """Pluralises a string.

    Substrings of the form `plural(N|X|Y)` with are replaced with X if N is
    an integer and is 1, and Y otherwise.

    For specific languages a Substring form of 'plural(N|X|Y|LANG|S)' 
    can be used to pass the pluraliser a language code and special information
    Check the polish language translation for more information!
    """
    plural = re.compile(r"plural\(([^|]+)\|([^|]+)\|([^|]+)(?:\|([^|]*))?(?:\|([^|]*))?\)")
    return plural.sub(make_plural, string)


def make_plural(match: Match[str]) -> str:
    """Returns the single or plural result from a pluralisation match."""
    amount_str, single, multiple, lang, special = match.groups()

    try:
        amount = int(amount_str)
    except ValueError:
        return multiple
    
    if lang == "PL": # Polish handling
        if amount == 1:
            return single
        
        # This condition checks for a specific plural form used in polish
        # it returns true for numbers ending 2,3 or 4 
        # except endings with 12, 13 or 14 which are exceptions
        elif 2 <= amount % 10 <= 4 and not (12 <= amount % 100 <= 14):
            return special
        return multiple
    
    else: # Regular handling
        if amount == 1:
            return single
        return multiple

def finalise_digest(digest: str) -> str:
    """Performs final postprocessing on a digest."""
    return emojize(pluralise(digest), variant="emoji_type")


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
    ids: Set[str] = set()
    return sorted(
        ids.union(
            *cast(Iterable[str], [group.keys() for group in post_groups])
        ),
        key=lambda id: sum(len(group[id]) for group in post_groups),
        reverse=True,
    )
