import re
import time
from re import Match, Pattern
from typing import Callable, List, Tuple, Union, cast

from notifier.types import DeliveryMethod


def r(regex: str) -> Pattern:
    """Compiles a regular expression."""
    return re.compile(regex, flags=re.MULTILINE)


ReplacementList = List[
    Union[Tuple[str, str], Tuple[Pattern, Union[str, Callable[[Match], str]]]]
]

replacements_to_html: ReplacementList = [
    # Alignment
    ("[[=]]", """<div style="text-align: center">"""),
    ("[[/=]]", "</div>"),
    # Wikidot user elements
    (r(r"\[\[\*?user (.*?)\]\]"), r"\1"),
    # Wikidot date elements
    (
        r(r"\[\[date ([0-9]+) format=\"([^|]*).*?\"\]\]"),
        lambda match: time.strftime(match[2], time.gmtime(int(match[1]))),
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
    # Links
    (r(r"\[(\S+) (.+?)\]"), r"""<a href="\1">\2</a>"""),
    # Headings
    (
        r(r"^(\++) (.+)$"),
        lambda match: "<h{0}>{1}</h{0}>".format(len(match[1]), match[2]),
    ),
    # Dashes
    ("--", "&mdash;"),
    # Bullets
    (r(r"^\* (.+)$"), r"<ul><li>\1</li></ul>"),
    # Remove unnecessary breaks effected by Wikidot's lax spacing
    ("\n", ""),
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
