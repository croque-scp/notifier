import sys
from pathlib import Path
from typing import Literal, cast

from notifier.digest import Digester
from tests.test_digest import fake_posts, fake_user_config

if __name__ == "__main__":
    lang = sys.argv[1]
    assert sys.argv[2] in ("pm", "email")
    delivery = cast(Literal["pm", "email"], sys.argv[2])
    user = fake_user_config
    user["language"] = lang
    user["delivery"] = delivery
    posts = fake_posts()
    digester = Digester(str(Path.cwd() / "config" / "lang.toml"))
    subject, digest = digester.for_user(user, posts)
    print("Subject:", subject)
    print(digest)
