import json
import logging
from typing import Any, Dict, List, Tuple, cast

import boto3
import tomlkit
from tomlkit.exceptions import TOMLKitError

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.database.utils import try_cache
from notifier.types import LocalConfig, SupportedWikiConfig
from notifier.wikidot import Wikidot

logger = logging.getLogger(__name__)

# For ease of parsing, configurations are coerced to TOML format
wiki_config_listpages_body = '''
id = "%%form_data{id}%%"
name = """%%title%%""" # Vulnerability if titles are editable publicly
secure = %%form_data{secure}%%
'''


def get_global_config(
    local_config: LocalConfig,
    database: BaseDatabaseDriver,
    wikidot: Wikidot,
) -> None:
    """Retrieve remote global config for wikis."""
    try_cache(
        get=lambda: fetch_supported_wikis(local_config, wikidot),
        store=database.store_supported_wikis,
        do_not_store=[],
    )


def fetch_supported_wikis(
    local_config: LocalConfig, wikidot: Wikidot
) -> List[SupportedWikiConfig]:
    """Fetch the list of supported wikis from the configuration wiki."""
    configs = []
    for config_soup in wikidot.listpages(
        local_config["config_wiki"],
        category=local_config["wiki_config_category"],
        module_body=wiki_config_listpages_body,
    ):
        raw_config = config_soup.get_text()
        try:
            configs.append(parse_raw_wiki_config(raw_config))
        except (TOMLKitError, AssertionError) as error:
            logger.error(
                "Could not parse wiki config %s",
                {
                    "raw_config": raw_config,
                    "first_line": next(filter(bool, raw_config.split("\n"))),
                },
                exc_info=error,
            )
            continue
    return configs


def parse_raw_wiki_config(raw_config: str) -> SupportedWikiConfig:
    """Parses a raw wiki config to a suitable format."""
    config = tomlkit.parse(raw_config)
    assert isinstance(config, dict)
    assert "id" in config
    assert "secure" in config
    assert config["secure"] in (0, 1)
    return cast(SupportedWikiConfig, config)


class AWS:
    """Methods for interacting with AWS."""

    session = None
    client = None

    @staticmethod
    def _get_client(region_name: str) -> Any:
        """Makes or retrieves a connection client."""
        if AWS.client is None:
            AWS.session = boto3.session.Session()
            AWS.client = AWS.session.client(
                service_name="secretsmanager", region_name=region_name
            )
        return AWS.client

    @staticmethod
    def get_secrets(
        region_name: str, secret_name: str, mapping: List[Tuple[str, str]]
    ) -> Dict[str, str]:
        """Retrieves secrets from Secrets Manager."""
        secrets = json.loads(
            AWS._get_client(region_name).get_secret_value(
                SecretId=secret_name
            )["SecretString"]
        )
        for key, _ in mapping:
            if key not in secrets:
                raise KeyError(f"Key {key} not found in secret {secret_name}")
        return {
            local_key: secrets[external_key]
            for external_key, local_key in mapping
        }
