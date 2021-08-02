from datetime import datetime

import feedparser
from bs4 import BeautifulSoup

from notifier.config.user import parse_thread_url
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.wikiconnection import Connection

not_yet_checked = object()

# HTTPS for the RSS feed doesn't work for insecure wikis, but HTTP does
# work for secure wikis
new_posts_rss = "http://{}.wikidot.com/feed/forum/posts.xml"

rss_timestamp_format = "%a, %d %b %Y %X %z"


def get_new_posts(database: BaseDatabaseDriver, connection: Connection):
    """For each configured wiki, retrieve and store new posts."""


def fetch_new_posts_rss(wiki_id: str):
    """Get new posts from the wiki's RSS feed."""
    rss_url = new_posts_rss.format(wiki_id)
    try:
        feed = feedparser.parse(rss_url)
    except Exception:  # pylint: disable=broad-except
        print("Caught exception when trying to parse feed", Exception)
    posts = [
        dict(
            zip(("thread_id", "id"), parse_thread_url(entry["id"])),
            parent_post_id=not_yet_checked,
            posted_timestamp=rss_datetime_to_timestamp(entry["published"]),
            title=entry["title"],
            snippet=make_post_snippet(entry["contents"]),
            user_id=entry["wikidot_authoruserid"],
            username=entry["wikidot_authorname"],
        )
        for entry in feed["entries"]
    ]
    return posts


def make_post_snippet(raw_contents: str) -> str:
    """Truncate a post's contents to elicit a snippet."""
    contents = BeautifulSoup(raw_contents, "html.parser").get_text()
    if len(contents) >= 80:
        contents = contents[:75] + "..."
    return contents


def rss_datetime_to_timestamp(time: str) -> int:
    """Convert an RSS datetime to a UTC timestamp.

    The timestamps from Wikidot's RSS are GMT.
    """
    return int(datetime.strptime(time, rss_timestamp_format).timestamp())
