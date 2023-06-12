from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from notifier.parsethread import get_user_from_nametag


def test_get_user_from_nametag() -> None:
    @dataclass
    class UserTag:
        description: str
        tag_raw: Tag
        expected_user_id: Optional[str]
        expected_username: Optional[str]

        def __post_init__(self):
            self.tag = BeautifulSoup(self.tag_raw, "html.parser").find(
                class_="printuser"
            )

            # Usernames have a 20 character limit
            if self.expected_username is not None:
                assert len(self.expected_username) <= 20

    user_tags = [
        UserTag(
            "Anonymous user with visible IP",
            """<span class="printuser anonymous"><a href="javascript:;" onclick="WIKIDOT.page.listeners.anonymousUserInfo('75.142.217.5'); return false;"><img class="small" src="https://www.wikidot.com/common--images/avatars/default/a16.png" alt=""></a><a href="javascript:;" onclick="WIKIDOT.page.listeners.anonymousUserInfo('75.142.217.5'); return false;">Anonymous <span class="ip">(75.142.217.x)</span></a></span>""",
            None,
            None,
        ),
        UserTag(
            "Guest user",
            """<span class="printuser avatarhover"><a href="javascript:;"><img class="small" src="https://secure.gravatar.com/avatar.php?gravatar_id=d0f7d0914b3a679ead94c8a16168f63f&amp;default=https://www.wikidot.com/common--images/avatars/default/a16.png&amp;size=16" alt=""></a>chelonianmobile (guest)</span>""",
            None,
            "chelonianmobile",
        ),
        UserTag(
            "Deleted user",
            """<span class="printuser deleted" data-id="462110"><img class="small" src="https://www.wikidot.com/common--images/avatars/default/a16.png" alt="">(account deleted)</span>""",
            "462110",
            None,
        ),
        UserTag(
            "Normal user (from a forum post)",
            """<span class="printuser avatarhover"><a href="http://www.wikidot.com/user:info/croquembouche" onclick="WIKIDOT.page.listeners.userInfo(2893766); return false;"><img class="small" src="https://www.wikidot.com/avatar.php?userid=2893766&amp;amp;size=small&amp;amp;timestamp=1686573582" alt="Croquembouche" style="background-image:url(https://www.wikidot.com/userkarma.php?u=2893766)"></a><a href="http://www.wikidot.com/user:info/croquembouche" onclick="WIKIDOT.page.listeners.userInfo(2893766); return false;">Croquembouche</a></span>""",
            "2893766",
            "Croquembouche",
        ),
        UserTag(
            "System user",
            """<span class="printuser">Wikidot</span>""",
            None,
            "Wikidot",
        ),
    ]

    for user_tag in user_tags:
        assert (
            user_tag.expected_user_id,
            user_tag.expected_username,
        ) == get_user_from_nametag(user_tag.tag)
