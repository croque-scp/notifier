from typing import List, Literal, Tuple, TypedDict, Union

import tomlkit
from bs4 import BeautifulSoup

from notifier.config.tool import LocalConfig
from notifier.database import DatabaseDriver
from notifier.database.driver import BaseDatabaseDriver
from notifier.wikiconnection import Connection

# For ease of parsing, configurations are coerced to TOML format
user_config_listpages_body = '''
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
    sub: Union[Literal[-1], Literal[1]]


class UserConfig(TypedDict):
    user_id: str
    username: str
    frequency: str
    language: str
    subscriptions: List[Subscription]
    unsubscriptions: List[Subscription]


def fetch_user_configs(
    local_config: LocalConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
):
    """Fetches a list of user configurations from the configuration wiki.

    User configurations are stored on the dedicated Wikidot site. They are
    cached in the SQLite database.
    """
    for raw_config in connection.listpages(
        local_config["config_wiki"],
        category=local_config["user_config_category"],
        module_body=user_config_listpages_body,
    ):
        raw_config = raw_config.get_text()
        try:
            config = parse_raw_user_config(raw_config)
        except:
            # If the parse fails, the user was probably trying code
            # injection or something - discard it
            print("Skipping config for", raw_config.split("\n")[0])
            continue
        category, slug = config["slug"].split(":")
        if category != "notify":
            continue
        if slug != config["username"]:
            # Only accept configs for the user who created the page
            continue
        # Store this config in the database
        raise NotImplementedError


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


def parse_subscriptions(urls: str) -> List[Subscription]:
    pass


def parse_thread_url(url: str) -> Tuple[str, Union[str, None]]:
    """Parses a URL to a wiki ID, thread ID and optionally a post ID."""
