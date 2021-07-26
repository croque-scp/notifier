from typing import Tuple, TypedDict, Union

import tomlkit
from bs4 import BeautifulSoup

from notifier.database import DatabaseDriver
from notifier.wikiconnection import Connection

# For ease of parsing, configurations are coerced to TOML format
listpages_body = '''
slug = "%%fullname%%"
username = "%%created_by_unix%%"
user_id = "%%created_by_id%%"
frequency = "%%form_raw{frequency}%%"
language = "%%form_raw{language}%%"
subscriptions = """
%%form_data{subscriptions}%%"""
unsubscriptions = """
%%form_data{unsubscriptions}%%"""
'''


class Subscription(TypedDict):
    thread_id: str
    post_id: Union[str, None]
    sub: Union[-1, 1]


class UserConfig(TypedDict):
    user_id: str
    username: str
    frequency: str
    language: str
    subscriptions: list[Subscription]
    unsubscriptions: list[Subscription]


def fetch_user_configs(database: DatabaseDriver, connection: Connection):
    """Fetches a list of user configurations from the configuration wiki.

    User configurations are stored on the dedicated Wikidot site. They are
    cached in the SQLite database."""

    for page in connection.listpages(
        "tars",
        category="notify",
        order="updated_at desc",
        module_body=listpages_body,
    ):
        page = BeautifulSoup(page["body"], "html.parser")
        configs = page.find(class_="list-pages-box").find_all("p")
        for raw_config in configs:
            raw_config = raw_config.get_text()
            try:
                config = parse_raw_user_config(raw_config)
            except:
                # If the parse fails, the user was probably trying code
                # injection or something - discard it
                print(f"Skipping config for", raw_config.split("\n")[0])
                continue
            category, slug = config["slug"].split(":")
            if category != "notify":
                continue
            if slug != config["username"]:
                # Only accept configs for the user who created the page
                continue
            # Store this config in the database
            pass


def parse_raw_user_config(raw_config: str) -> UserConfig:
    """Parses a raw user config string to a suitable format."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    assert "slug" in config
    assert "username" in config
    assert "user_id" in config
    if "subscriptions" in config:
        # Parse them
        pass
    else:
        config["subscriptions"] = []
    if "unsubscriptions" in config:
        pass
    else:
        config["unsubscriptions"] = []


def parse_thread_url(url: str) -> Tuple[str, Union[str, None]]:
    """Parses a URL to a wiki ID, thread ID and optionally a post ID."""
