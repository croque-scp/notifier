from typing import List, Tuple, Union

import tomlkit
from tomlkit.exceptions import TOMLKitError

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import LocalConfig, Subscription, UserConfig
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
        except (TOMLKitError, AssertionError):
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
        # TODO


def parse_raw_user_config(raw_config: str) -> UserConfig:
    """Parses a raw user config string to a suitable format."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    assert "slug" in config
    assert "username" in config
    assert "user_id" in config
    if "subscriptions" in config:
        # Parse them TODO
        pass
    else:
        config["subscriptions"] = []
    if "unsubscriptions" in config:
        pass
    else:
        config["unsubscriptions"] = []
    # TODO


def parse_subscriptions(urls: str) -> List[Subscription]:
    # TODO
    pass


def parse_thread_url(url: str) -> Tuple[str, Union[str, None]]:
    """Parses a URL to a wiki ID, thread ID and optionally a post ID."""
