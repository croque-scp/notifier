from typing import Dict, List, Literal, TypedDict, Union

import requests
import tomlkit


class LocalConfig(TypedDict):
    wikidot_username: str
    user_config_wiki: str
    user_config_category: str
    support_sites_url: str
    overrides_url: str


class SupportedSiteConfig(TypedDict):
    secure: Union[Literal[0], Literal[1]]
    alts: List[str]


def read_local_config(path: str) -> LocalConfig:
    """Reads the local config file from the specified path.

    Raises AssertionError if there is a problem.
    """
    with open(path, "r") as config_file:
        config = tomlkit.parse(config_file.read())
    assert "wikidot_username" in config
    assert "user_config_wiki" in config
    assert "user_config_category" in config
    assert "supported_sites_url" in config
    assert "overrides_url" in config
    return config


def fetch_supported_sites(
    supported_sites_url: str,
) -> Dict[str, SupportedSiteConfig]:
    """Fetch the list of supported sites from the configuration wiki.

    Raises AssertionError if there is a problem, which must be handled.
    """
    sites = tomlkit.parse(requests.get(supported_sites_url))
    assert isinstance(sites, dict)
    for settings in sites.values():
        assert settings["secure"] in (0, 1)
        assert isinstance(settings["alts"], list)
        assert all(isinstance(alt, str) for alt in settings["alts"])
    return sites
