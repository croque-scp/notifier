import re
from pathlib import Path
from typing import Any, List, cast

import requests
import tomlkit
from tomlkit.exceptions import TOMLKitError
from typing_extensions import TypeGuard

from notifier.database.drivers.base import BaseDatabaseDriver, try_cache
from notifier.types import (
    GlobalOverridesConfig,
    LocalConfig,
    SupportedWikiConfig,
)
from notifier.wikiconnection import Connection

# For ease of parsing, configurations are coerced to TOML format
wiki_config_listpages_body = '''
id = "%%form_data{id}%%"
name = """%%title%%""" # Vulnerability if titles are editable publicly
secure = %%form_data{secure}%%
'''


def read_local_config(config_path: str) -> LocalConfig:
    """Reads the local config file from the specified path.

    Raises AssertionError if there is a problem.
    """
    with open(config_path, "r") as config_file:
        config = cast(dict, tomlkit.parse(config_file.read()))

    def replace_path_alias(path: str) -> str:
        path = re.sub(r"^@", str(Path(__file__).parent.parent), path)
        path = re.sub(r"^\?", config_path, path)
        return path

    def assert_key(config: dict, key: str, instance: Any) -> None:
        if not isinstance(config.get(key), instance):
            raise KeyError(f"Missing {key} in config")

    def is_complete_config(config: dict) -> TypeGuard[LocalConfig]:
        assert_key(config, "wikidot_username", str)
        assert_key(config, "config_wiki", str)
        assert_key(config, "user_config_category", str)
        assert_key(config, "wiki_config_category", str)
        assert_key(config, "overrides_url", str)
        assert_key(config, "path", dict)
        assert_key(config["path"], "lang", str)
        config["path"]["lang"] = replace_path_alias(config["path"]["lang"])
        return True

    if is_complete_config(config):
        return config
    raise RuntimeError


def get_global_config(
    local_config: LocalConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
) -> None:
    """Retrieve remote global config for overrides and wikis."""
    try_cache(
        get=lambda: fetch_global_overrides(local_config),
        store=database.store_global_overrides,
        do_not_store={},
    )
    try_cache(
        get=lambda: fetch_supported_wikis(local_config, connection),
        store=database.store_supported_wikis,
        do_not_store=[],
    )


def fetch_global_overrides(local_config: LocalConfig) -> GlobalOverridesConfig:
    """Get the list of global override actions from the configuration
    wiki."""
    raw_config = requests.get(local_config["overrides_url"]).text
    config = {}
    try:
        config = parse_raw_overrides_config(raw_config)
    except (TOMLKitError, AssertionError):
        print("Couldn't parse global overrides config")
    return config


def parse_raw_overrides_config(raw_config: str) -> GlobalOverridesConfig:
    """Parses a raw overrides config to lists of override objects sorted by
    the wiki ID they correspond to."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    for overrides in config.values():
        assert isinstance(overrides, list)
        for override in overrides:
            assert "action" in override
    return config


def fetch_supported_wikis(
    local_config: LocalConfig, connection: Connection
) -> List[SupportedWikiConfig]:
    """Fetch the list of supported wikis from the configuration wiki."""
    configs = []
    for config_soup in connection.listpages(
        local_config["config_wiki"],
        category=local_config["wiki_config_category"],
        module_body=wiki_config_listpages_body,
    ):
        raw_config = config_soup.get_text()
        try:
            configs.append(parse_raw_wiki_config(raw_config))
        except (TOMLKitError, AssertionError):
            print("Couldn't parse wiki:", raw_config.split("\n")[0])
            continue
    return configs


def parse_raw_wiki_config(raw_config: str) -> SupportedWikiConfig:
    """Parses a raw wiki config to a suitable format."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    assert "id" in config
    assert "secure" in config
    assert config["secure"] in (0, 1)
    return config
