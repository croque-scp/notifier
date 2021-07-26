from typing import TypedDict
import tomlkit


class LocalConfig(TypedDict):
    wikidot_username: str
    user_config_wiki: str
    user_config_category: str
    support_sites_url: str
    overrides_url: str


def read_local_config(path: str) -> LocalConfig:
    """Reads the local config file from the specified path."""
    with open(path, "r") as config_file:
        config = tomlkit.parse(config_file.read())
    assert "wikidot_username" in config
    assert "user_config_wiki" in config
    assert "user_config_category" in config
    assert "supported_sites_url" in config
    assert "overrides_url" in config
    return config


def fetch_supported_sites():
    """Fetch the list of supported sites from the configuration wiki."""
    pass
