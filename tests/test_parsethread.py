from dataclasses import dataclass
from typing import Optional, cast

from bs4 import BeautifulSoup
from bs4.element import Tag

from notifier.parsethread import count_pages, get_user_from_nametag

# pylint:disable=missing-function-docstring
# pylint:disable=missing-class-docstring


def test_get_user_from_nametag() -> None:
    @dataclass
    class UserTag:
        description: str
        tag_raw: str
        expected_user_id: Optional[str]
        expected_username: Optional[str]

        def __post_init__(self) -> None:
            self.tag = cast(
                Tag,
                BeautifulSoup(self.tag_raw, "html.parser").find(
                    class_="printuser"
                ),
            )

            # Usernames have a 20 character limit
            if self.expected_username is not None:
                assert len(self.expected_username) <= 20

        def test(self) -> None:
            assert (
                self.expected_user_id,
                self.expected_username,
            ) == get_user_from_nametag(self.tag)

    UserTag(
        "Anonymous user with visible IP",
        """<span class="printuser anonymous"><a href="javascript:;" onclick="WIKIDOT.page.listeners.anonymousUserInfo('75.142.217.5'); return false;"><img class="small" src="https://www.wikidot.com/common--images/avatars/default/a16.png" alt=""></a><a href="javascript:;" onclick="WIKIDOT.page.listeners.anonymousUserInfo('75.142.217.5'); return false;">Anonymous <span class="ip">(75.142.217.x)</span></a></span>""",
        None,
        None,
    ).test()
    UserTag(
        "Guest user",
        """<span class="printuser avatarhover"><a href="javascript:;"><img class="small" src="https://secure.gravatar.com/avatar.php?gravatar_id=d0f7d0914b3a679ead94c8a16168f63f&amp;default=https://www.wikidot.com/common--images/avatars/default/a16.png&amp;size=16" alt=""></a>chelonianmobile (guest)</span>""",
        None,
        "chelonianmobile",
    ).test()
    UserTag(
        "Guest user",
        """<span class="printuser avatarhover"><a href="javascript:;"><img class="small" src="https://secure.gravatar.com/avatar.php?gravatar_id=b804142d40e0801797a7a7616c31d351&amp;default=https://www.wikidot.com/common--images/avatars/default/a16.png&amp;size=16" alt=""/></a>Dr Thomas (guest)</span> <span class="odate time_1236187867 format_%25e%20%25b%20%25Y%2C%20%25H%3A%25M%7Cagohover">04 Mar 2009 17:31</span>""",
        None,
        "Dr Thomas",
    ).test()
    UserTag(
        "Deleted user",
        """<span class="printuser deleted" data-id="462110"><img class="small" src="https://www.wikidot.com/common--images/avatars/default/a16.png" alt="">(account deleted)</span>""",
        "462110",
        None,
    ).test()
    UserTag(
        "Normal user (from a forum post)",
        """<span class="printuser avatarhover"><a href="https://www.wikidot.com/user:info/croquembouche" onclick="WIKIDOT.page.listeners.userInfo(2893766); return false;"><img class="small" src="https://www.wikidot.com/avatar.php?userid=2893766&amp;amp;size=small&amp;amp;timestamp=1686573582" alt="Croquembouche" style="background-image:url(https://www.wikidot.com/userkarma.php?u=2893766)"></a><a href="https://www.wikidot.com/user:info/croquembouche" onclick="WIKIDOT.page.listeners.userInfo(2893766); return false;">Croquembouche</a></span>""",
        "2893766",
        "Croquembouche",
    ).test()
    UserTag(
        "System user",
        """<span class="printuser">Wikidot</span>""",
        None,
        "Wikidot",
    ).test()


def test_count_pages() -> None:
    @dataclass
    class Pager:
        html: str
        expected_current_page: int
        expected_page_count: int

        def test(self) -> None:
            assert (
                self.expected_page_count,
                self.expected_current_page,
            ) == count_pages(self.html)

    Pager(
        """<div class="forum-category-box">
            <div class="pager">
                <span class="pager-no">page 1 of 263</span>
                <span class="current">1</span>
                <span class="target"><a href="/forum/c-00000/p/2">2</a></span>
                <span class="target"><a href="/forum/c-00000/p/3">3</a></span>
                <span class="dots">...</span>
                <span class="target"><a href="/forum/c-00000/p/262">262</a></span>
                <span class="target"><a href="/forum/c-00000/p/263">263</a></span>
                <span class="target"><a href="/forum/c-00000/p/2">next »</a></span>
            </div>
        </div>""",
        1,
        263,
    ).test()
    Pager(
        """<div class="pager">
            <span class="pager-no">page 262 of 263</span>
            <span class="target"><a href="/forum/c-891087/p/261">« previous</a></span>
            <span class="target"><a href="/forum/c-891087/p/1">1</a></span>
            <span class="target"><a href="/forum/c-891087/p/2">2</a></span>
            <span class="dots">...</span>
            <span class="target"><a href="/forum/c-891087/p/260">260</a></span>
            <span class="target"><a href="/forum/c-891087/p/261">261</a></span>
            <span class="current">262</span>
            <span class="target"><a href="/forum/c-891087/p/263">263</a></span>
            <span class="target"><a href="/forum/c-891087/p/263">next »</a></span>
        </div>""",
        262,
        263,
    ).test()
