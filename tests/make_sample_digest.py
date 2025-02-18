import sys
from pathlib import Path

from notifier.composer import Composer
from tests.test_digest import fake_posts, fake_user  # type:ignore

if __name__ == "__main__":
    lang = sys.argv[1]
    delivery = sys.argv[2]
    assert delivery in ["pm", "email"]
    user = fake_user.__pytest_wrapped__.obj()
    user["language"] = lang
    user["delivery"] = delivery
    posts = fake_posts.__pytest_wrapped__.obj(user)
    composer = Composer(str(Path.cwd() / "config" / "lang.toml"))
    subject, digest = composer.for_user(user, posts)
    print("Subject:", subject)
    print(digest)
