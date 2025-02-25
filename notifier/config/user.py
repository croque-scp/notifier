import logging
from operator import itemgetter
import re
from typing import List, Optional, Tuple, TypedDict, Union, cast

import tomlkit
from tomlkit.exceptions import TOMLKitError

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.utils import try_cache
from notifier.parsethread import get_timestamp
from notifier.types import (
    LocalConfig,
    RawUserConfig,
    Subscription,
    SubscriptionCardinality,
)
from notifier.wikidot import Wikidot

logger = logging.getLogger(__name__)


# For ease of parsing, configurations are coerced to TOML format
user_config_listpages_body = '''
slug = """%%fullname%%"""
username = """%%created_by%%"""
user_id = "%%created_by_id%%"
frequency = "%%form_raw{frequency}%%"
language = "%%form_raw{language}%%"
delivery = "%%form_raw{method}%%"
user_base_notified = """%%created_at%%"""
tags = """%%tags%%"""
subscriptions = """
%%form_data{subscriptions}%%"""
unsubscriptions = """
%%form_data{unsubscriptions}%%"""
'''


def get_user_config(
    local_config: LocalConfig,
    database: BaseDatabaseDriver,
    wikidot: Wikidot,
) -> None:
    """Retrieve remote user config."""
    try_cache(
        get=lambda: find_valid_user_configs(local_config, wikidot),
        store=database.store_user_configs,
        do_not_store=[],
    )


def find_valid_user_configs(
    local_config: LocalConfig, wikidot: Wikidot
) -> List[RawUserConfig]:
    """Fetches user configs and returns those that are valid."""
    configs: List[RawUserConfig] = []
    for slug, config in fetch_user_configs(local_config, wikidot):
        if not user_config_is_valid(slug, config):
            # Only accept configs for the user who created the page
            logger.warning(
                "Skipping user config %s",
                {
                    "username": config["username"],
                    "slug": slug,
                    "reason": "wrong slug for user ID",
                },
            )
            continue
        configs.append(config)
    return configs


def user_config_is_valid(slug: str, config: RawUserConfig) -> bool:
    """Determines whether a user config is permitted to exist given its
    slug and the ID of the user that created it."""
    return ":" in slug and slug.split(":")[1] == config["user_id"]


class UserConfigFetchResult(TypedDict):
    """Result of fetching user configs, including valid configs and invalid configs to be deleted later."""

    valid: List[Tuple[str, RawUserConfig]]
    invalid: List[Tuple[str, RawUserConfig]]


def fetch_user_configs(
    local_config: LocalConfig, wikidot: Wikidot, database: BaseDatabaseDriver
) -> UserConfigFetchResult:
    """Fetches the list of user configs.

    Returns both valid configs (to be stored) and invalid configs (to be removed)."""
    # TODO Use listpages filter 'updated_at="last X hour"' to only fetch new/updated pages
    return {
        "valid": [],
        "invalid": [],
    }


def fetch_user_configs_OLD(
    local_config: LocalConfig, wikidot: Wikidot
) -> List[Tuple[str, RawUserConfig]]:
    """Fetches a list of user configurations from the configuration wiki.

    User configurations are stored on the dedicated Wikidot site. They are
    cached in the database.
    """
    configs: List[Tuple[str, RawUserConfig]] = []
    for config_soup in wikidot.listpages(
        local_config["config_wiki_id"],
        category=local_config["user_config_category"],
        module_body=user_config_listpages_body,
    ):
        raw_config = config_soup.get_text()
        # The timestamp of the page's creation date is in the class of a
        # timestamp element, so cannot be extracted by get_text
        user_timestamp = get_timestamp(config_soup)
        try:
            config, slug = parse_raw_user_config(
                raw_config,
                user_timestamp,
                local_config["service_start_timestamp"],
            )
        except (TOMLKitError, AssertionError) as error:
            # If the parse fails, the user was probably trying code
            # injection or something - discard it
            logger.error(
                "Could not parse user config %s",
                {
                    "raw_config": raw_config,
                    "first_line": next(filter(bool, raw_config.split("\n"))),
                },
                exc_info=error,
            )
            continue
        configs.append((slug, config))
    return configs


def parse_raw_user_config(
    raw_config: str,
    user_timestamp: Optional[int],
    service_start_timestamp: int,
) -> Tuple[RawUserConfig, str]:
    """Parses a raw user config string to a suitable format, also returning
    the config slug."""
    config = dict(tomlkit.parse(raw_config))
    slug = config.pop("slug", "")
    assert isinstance(slug, str)
    assert "username" in config
    assert "user_id" in config
    # Parse page date to approximate timestamp and coerce to int
    config["user_base_notified"] = max(
        user_timestamp or 0, service_start_timestamp
    )
    assert "tags" in config
    assert isinstance(config["tags"], str)
    config["subscriptions"] = parse_subscriptions(
        config.get("subscriptions", ""), 1
    )
    config["unsubscriptions"] = parse_subscriptions(
        config.get("unsubscriptions", ""), -1
    )
    return cast(RawUserConfig, dict(config)), slug


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
            thread_id, post_id = itemgetter("thread_id", "post_id")(
                parse_thread_url(url)
            )
        except ValueError:
            # The URL parser is extremely forgiving, so this should not
            # happen; if it somehow does, discard it
            continue
        subscriptions.append(
            {"thread_id": thread_id, "post_id": post_id, "sub": cardinality}
        )
    return subscriptions


ThreadPostIds = TypedDict(
    "ThreadPostIds", {"thread_id": str, "post_id": Union[str, None]}
)


def parse_thread_url(
    url: str,
) -> ThreadPostIds:
    """Parses a URL to a thread ID and optionally a post ID."""
    pattern = re.compile(r"(t-[0-9]+)(?:.*#(post-[0-9]+))?")
    match = pattern.search(url)
    if not match:
        raise ValueError("Thread URL does not match expected pattern")
    thread_id, post_id = match.groups()
    return {"thread_id": thread_id, "post_id": post_id}
