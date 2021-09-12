import re
from typing import List, Tuple, Union

import tomlkit
from tomlkit.exceptions import TOMLKitError

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.utils import try_cache
from notifier.types import (
    LocalConfig,
    RawUserConfig,
    Subscription,
    SubscriptionCardinality,
)
from notifier.wikiconnection import Connection

# For ease of parsing, configurations are coerced to TOML format
user_config_listpages_body = '''
slug = "%%fullname%%"
username = "%%created_by_unix%%"
user_id = "%%created_by_id%%"
frequency = "%%form_raw{frequency}%%"
language = "%%form_raw{language}%%"
delivery = "%%form_raw{method}%%"
subscriptions = """
%%form_data{subscriptions}%%"""
unsubscriptions = """
%%form_data{unsubscriptions}%%"""
'''


def get_user_config(
    local_config: LocalConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
):
    """Retrieve remote user config."""
    try_cache(
        get=lambda: fetch_user_configs(local_config, connection),
        store=database.store_user_configs,
        do_not_store=[],
    )


def fetch_user_configs(
    local_config: LocalConfig,
    connection: Connection,
) -> List[RawUserConfig]:
    """Fetches a list of user configurations from the configuration wiki.

    User configurations are stored on the dedicated Wikidot site. They are
    cached in the database.
    """
    configs: List[RawUserConfig] = []
    for config_soup in connection.listpages(
        local_config["config_wiki"],
        category=local_config["user_config_category"],
        module_body=user_config_listpages_body,
    ):
        raw_config = config_soup.get_text()
        try:
            config, slug = parse_raw_user_config(raw_config)
        except (TOMLKitError, AssertionError):
            # If the parse fails, the user was probably trying code
            # injection or something - discard it
            print("Couldn't parse user config:", raw_config.split("\n")[0])
            continue
        if (
            ":" not in slug
            or slug.split(":")[1].casefold() != config["username"].casefold()
        ):
            # Only accept configs for the user who created the page
            print(f"Wrong slug {slug} for {config['username']}")
            continue
        configs.append(config)
    return configs


def parse_raw_user_config(raw_config: str) -> Tuple[RawUserConfig, str]:
    """Parses a raw user config string to a suitable format, also returning
    the config slug."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    slug = config.pop("slug", "")
    assert isinstance(slug, str)
    assert "username" in config
    assert "user_id" in config
    config["subscriptions"] = parse_subscriptions(
        config.get("subscriptions", []), 1
    )
    config["unsubscriptions"] = parse_subscriptions(
        config.get("unsubscriptions", []), -1
    )
    return config, slug


def parse_subscriptions(
    urls: str, cardinality: SubscriptionCardinality
) -> List[Subscription]:
    """Parse a list of thread/post URLs to a list of subscriptions."""
    subscriptions: List[Subscription] = []
    for url in urls.split("\n"):
        if not re.search(r"t-[0-9]", url):
            # The URL doesn't contain a thread ID, so discard it
            # (Empty rows are permitted so this is valid)
            continue
        try:
            thread_id, post_id = parse_thread_url(url)
        except ValueError:
            # The URL parser is extremely forgiving, so this should not
            # happen; if it somehow does, discard it
            continue
        subscriptions.append(
            {"thread_id": thread_id, "post_id": post_id, "sub": cardinality}
        )
    return subscriptions


def parse_thread_url(url: str) -> Tuple[str, Union[str, None]]:
    """Parses a URL to a thread ID and optionally a post ID."""
    pattern = re.compile(r"(t-[0-9]+)(?:.*#(post-[0-9]+))?")
    match = pattern.search(url)
    if not match:
        raise ValueError("Thread URL does not match expected pattern")
    thread_id, post_id = match.groups()
    return thread_id, post_id
