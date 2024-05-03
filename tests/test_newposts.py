from _pytest.monkeypatch import MonkeyPatch
from notifier.newposts import fetch_new_posts_rss


sample_rss_xml = """
<rss version="2.0">
    <channel>
        <title>SCP Foundation - new forum posts</title>
        <link>http://scp-wiki.wikidot.com/forum/start</link>
            <description>
            Posts in forums of the site "SCP Foundation" - Secure, Contain, Protect
        </description>
        <copyright/>
        <lastBuildDate>Fri, 03 May 1970 16:26:04 +0000</lastBuildDate>
        <item>
            <guid>
                http://scp-wiki.wikidot.com/forum/t-1#post-11
            </guid>
            <title>Sample title</title>
            <link>
                http://scp-wiki.wikidot.com/forum/t-1/sample-title#post-11
            </link>
            <description/>
            <pubDate>Tue, 14 Nov 2023 22:13:20 GMT +0000</pubDate>
            <wikidot:authorName>FakeUsername</wikidot:authorName>
            <wikidot:authorUserId>11111</wikidot:authorUserId>
            <content:encoded>
                <p>Sample text
            </content:encoded>
        </item>
        <item>
            <guid>
                http://scp-wiki.wikidot.com/forum/t-2#post-21
            </guid>
            <title/>
            <link>
                http://scp-wiki.wikidot.com/forum/t-2/sample-title#post-21
            </link>
            <description/>
            <pubDate>Tue, 14 Nov 2023 22:13:20 GMT +0000</pubDate>
            <wikidot:authorName>FakeUsername</wikidot:authorName>
            <wikidot:authorUserId>11111</wikidot:authorUserId>
            <content:encoded>
                <p>Sample text
            </content:encoded>
        </item>
        <item>
            <guid>
                http://scp-wiki.wikidot.com/forum/t-3#post-31
            </guid>
            <title>Sample title</title>
            <link>
                http://scp-wiki.wikidot.com/forum/t-3/sample-title#post-31
            </link>
            <description/>
            <pubDate>Tue, 14 Nov 2023 22:13:20 GMT +0000</pubDate>
            <wikidot:authorName>FakeUsername</wikidot:authorName>
            <wikidot:authorUserId>11111</wikidot:authorUserId>
            <content:encoded>
                <p>Sample text
            </content:encoded>
        </item>
        <item>
            <guid>
                http://scp-wiki.wikidot.com/forum/t-4#post-41
            </guid>
            <title/>
            <link>
                http://scp-wiki.wikidot.com/forum/t-4/sample-title#post-41
            </link>
            <description/>
            <pubDate>Tue, 14 Nov 2023 22:13:20 GMT +0000</pubDate>
            <wikidot:authorName>FakeUsername</wikidot:authorName>
            <wikidot:authorUserId>11111</wikidot:authorUserId>
            <content:encoded>
                <p>Sample text
            </content:encoded>
        </item>
    </channel>
</rss>
"""


def test_rss_parse(monkeypatch: MonkeyPatch) -> None:
    """Test that RSS feeds are parsed as expected."""

    # Disable wiki_id to URL interpolation
    monkeypatch.setattr("notifier.newposts.new_posts_rss", "{}")

    new_posts = list(fetch_new_posts_rss(sample_rss_xml))
    assert new_posts == [
        {
            "thread_id": "t-1",
            "post_id": "post-11",
            "posted_timestamp": 1700000000,
        },
        {
            "thread_id": "t-2",
            "post_id": "post-21",
            "posted_timestamp": 1700000000,
        },
        {
            "thread_id": "t-3",
            "post_id": "post-31",
            "posted_timestamp": 1700000000,
        },
        {
            "thread_id": "t-4",
            "post_id": "post-41",
            "posted_timestamp": 1700000000,
        },
    ]
