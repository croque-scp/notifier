import sys
from pathlib import Path

from notifier.digest import Digester
from tests.test_digest import fake_posts, fake_user

if __name__ == "__main__":
    lang = sys.argv[1]
    delivery = sys.argv[2]
    assert delivery in ["pm", "email"]
    user = fake_user.__pytest_wrapped__.obj()
    user["language"] = lang
    user["delivery"] = delivery
    posts = fake_posts.__pytest_wrapped__.obj(user)
    digester = Digester(str(Path.cwd() / "config" / "lang.toml"))
    subject, digest = digester.for_user(user, posts)
    print("Subject:", subject)
    print(digest)
