from typing import Dict, List, Literal, Optional, TypedDict, Union

import requests
import tomlkit
from tomlkit.exceptions import TOMLKitError

from notifier.database.driver import BaseDatabaseDriver, get_or_get_from_cache
from notifier.wikiconnection import Connection

# For ease of parsing, configurations are coerced to TOML format
site_config_listpages_body = """
id = "%%form_data{id}%%"
secure = %%forum_data{secure}%%
"""


class LocalConfig(TypedDict):
    wikidot_username: str
    config_wiki: str
    user_config_category: str
    site_config_category: str
    overrides_url: str


class SupportedSiteConfig(TypedDict):
    id: str
    secure: Union[Literal[0], Literal[1]]


class GlobalOverrideConfig(TypedDict):
    description: str
    action: str
    category_id_is: Optional[str]
    thread_id_is: Optional[str]
    thread_title_matches: Optional[str]


GlobalOverridesConfig = Dict[str, List[GlobalOverrideConfig]]


def read_local_config(path: str) -> LocalConfig:
    """Reads the local config file from the specified path.

    Raises AssertionError if there is a problem.
    """
    with open(path, "r") as config_file:
        config = tomlkit.parse(config_file.read())
    assert "wikidot_username" in config
    assert "config_wiki" in config
    assert "user_config_category" in config
    assert "site_config_category" in config
    assert "overrides_url" in config
    return config


def get_global_config(
    local_config: LocalConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
):
    overrides = get_or_get_from_cache(
        lambda: fetch_global_overrides(local_config),
        database.store_global_overrides,
        database.get_global_overrides,
        fail_value={},
    )
    sites = fetch_supported_sites(local_config, connection)


def fetch_global_overrides(local_config: LocalConfig) -> GlobalOverridesConfig:
    """Get the list of global override actions from the configuration
    wiki."""
    raw_config = requests.get(local_config["overrides_url"])
    config = {}
    try:
        config = parse_raw_overrides_config(raw_config)
    except (TOMLKitError, AssertionError):
        print("Couldn't parse global overrides config")
    return config


def fetch_supported_sites(
    local_config: LocalConfig, connection: Connection
) -> List[SupportedSiteConfig]:
    """Fetch the list of supported sites from the configuration wiki."""
    configs = []
    for raw_config in connection.listpages(
        local_config["config_wiki"],
        category=local_config["site_config_category"],
        module_body=site_config_listpages_body,
    ):
        try:
            configs.append(parse_raw_site_config(raw_config))
        except (TOMLKitError, AssertionError):
            print("Couldn't parse site:", raw_config.split("\n")[0])
            continue
    return configs


def parse_raw_site_config(raw_config: str) -> SupportedSiteConfig:
    """Parses a raw site config to a suitable format."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    assert "id" in config
    assert "secure" in config
    assert config["secure"] in (0, 1)
    return config


def parse_raw_overrides_config(raw_config: str) -> GlobalOverridesConfig:
    """Parses a raw overrides config to lists of override objects sorted by
    the wiki ID they correspond to."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    for wiki_id, overrides in config.items():
        assert isinstance(overrides, list)
        for override in overrides:
            assert "action" in override
    return config
