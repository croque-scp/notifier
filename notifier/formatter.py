import re
import time
from re import Match, Pattern
from typing import Callable, List, Tuple, Union, cast

replacements: List[
    Union[Tuple[str, str], Tuple[Pattern, Union[str, Callable[[Match], str]]]]
] = [
    # Alignment
    ("[[=]]", """<div style="text-align: center">"""),
    ("[[/=]]", "</div>"),
    # Wikidot user elements
    (re.compile(r"<\*?user (.*?)>"), "$1"),
    # Wikidot date elements
    (
        re.compile(r"\[\[date ([0-9]+) format=\"([^|]*).*?\"\]\]"),
        lambda match: time.strftime(match[2], time.gmtime(int(match[1]))),
    ),
    # Inline formatting
    (re.compile(r"//(.+?)//"), "<i>$1</i>"),
    (re.compile(r"\*\*(.+?)\*\*"), "<b>$1</b>"),
    (re.compile(r"##(\S+)\|(.+?)##"), """<span style="color: $1">$2</span>"""),
    # Remaining misc elements like ul/li
    ("[[", "<"),
    ("]]", ">"),
    # Links
    (re.compile(r"\[(\S+) (.+?)\]"), """<a href="$1">$2</a>"""),
    # Headings
    (
        re.compile(r"^(\++) (.+)$"),
        lambda match: "<h{0}>{1}</h{0}>".format(len(match[1]), match[2]),
    ),
    # Dashes
    ("--", "&mdash;"),
    # Bullets
    (re.compile(r"^\* (.+)$"), "<ul><li>$1</li></ul>"),
]


def convert_syntax_to_html(digest: str) -> str:
    """Converts Wikidot syntax roughly to HTML.

    Supports only a tiny subset of full Wikidot syntax and only does it
    approximately. Good enough for notifications.
    """
    for find, replace in replacements:
        if isinstance(find, str):
            digest = digest.replace(find, cast(str, replace))
        else:
            digest = find.sub(replace, digest)
    return digest
