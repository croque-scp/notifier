import re
import time
from typing import Callable, List, Tuple, Union, cast, Pattern, Match

from notifier.types import DeliveryMethod


def r(regex: str) -> Pattern[str]:
    """Compiles a regular expression."""
    return re.compile(regex, flags=re.MULTILINE)


ReplacementList = List[
    Union[
        Tuple[str, str],
        Tuple[Pattern[str], Union[str, Callable[[Match[str]], str]]],
    ]
]

replacements_to_html: ReplacementList = [
    # Alignment
    ("[[=]]", """<div style="text-align: center">"""),
    ("[[/=]]", "</div>"),
    # Wikidot date elements
    (
        r(r"\[\[date ([0-9]+) format=\"([^|]*).*?\"\]\]"),
        lambda match: time.strftime(match[2], time.gmtime(int(match[1]))),
    ),
    # Links
    (r(r"\[(\S+) (.+?)\]"), r"""<a href="\1">\2</a>"""),
    (
        r(r"\[\[\*?user (.*?)\]\]"),
        r"""<a href="https://www.wikidot.com/user:info/\1">\1</a>""",
    ),
    # Inline formatting
    (r(r"//(.+?)//"), r"<i>\1</i>"),
    (r(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (
        r(r"##(\S+)\|(.+?)##"),
        r"""<span style="color: \1">\2</span>""",
    ),
    # Remaining misc elements like ul/li
    ("[[", "<"),
    ("]]", ">"),
    # Headings
    (
        r(r"^(\++) (.+)$"),
        lambda match: "<h{0}>{1}</h{0}>".format(len(match[1]), match[2]),
    ),
    # Horizontal rules
    (r(r"^-{3,}$"), "<hr>"),
    # Dashes
    ("--", "&mdash;"),
    # Bullets
    (r(r"^\* (.+)$"), r"<ul><li>\1</li></ul>"),
    # Remove unnecessary breaks effected by Wikidot's lax spacing
    (r(r"\n+"), " "),
]

replacements_to_wikitext: ReplacementList = [("<br>", "")]


def convert_syntax(digest: str, method: DeliveryMethod) -> str:
    """Converts the pseudo-syntax used for digest templates to either full
    Wikitext or full HTML based on the intended delivery method.
    """
    for find, replace in {
        "email": replacements_to_html,
        "pm": replacements_to_wikitext,
    }[method]:
        if isinstance(find, str):
            digest = digest.replace(find, cast(str, replace))
        else:
            digest = find.sub(replace, digest)
    return digest
