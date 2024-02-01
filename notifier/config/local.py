import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, cast

import tomlkit
from typing_extensions import TypeGuard

from notifier.config.remote import AWS
from notifier.database.utils import resolve_driver_from_config
from notifier.types import AuthConfig, LocalConfig

logger = logging.getLogger(__name__)


def assert_key_for_scope(
    scope: str,
) -> Callable[[Dict[str, Any], str, Any], None]:
    """Checks that a key of the given name and type is present in a config."""

    def assert_key(config: Dict[str, Any], key: str, instance: Any) -> None:
        if not isinstance(config.get(key), instance):
            raise KeyError(f"Missing {key} in {scope}")

    return assert_key


def read_local_config(config_path: str) -> LocalConfig:
    """Reads the local config file from the specified path.

    Raises AssertionError if there is a problem.
    """
    logger.debug("Reading local config %s", {"path": config_path})
    with open(config_path, "r", encoding="utf-8") as config_file:
        config = cast(Dict[str, Any], tomlkit.parse(config_file.read()))
        logger.debug("Found config file")

    def replace_path_alias(path: str) -> str:
        path = re.sub(r"^@", str(Path(__file__).parent.parent), path)
        path = re.sub(r"^\?", config_path, path)
        return path

    def is_complete_config(config: Dict[str, Any]) -> TypeGuard[LocalConfig]:
        """Check that the config contains all required keys."""
        assert_key = assert_key_for_scope("main config")
        # Main config
        assert_key(config, "wikidot_username", str)
        assert_key(config, "config_wiki", str)
        assert_key(config, "user_config_category", str)
        assert_key(config, "wiki_config_category", str)
        assert_key(config, "gmail_username", str)
        assert_key(config, "service_start_timestamp", int)

        # Database section
        assert_key(config, "database", dict)
        assert_key(config["database"], "driver", str)
        assert_key(config["database"], "database_name", str)
        try:
            resolve_driver_from_config(config["database"]["driver"])
        except (ImportError, AttributeError) as error:
            raise ValueError("database_driver in config is invalid") from error

        # Paths section
        assert_key(config, "path", dict)
        assert_key(config["path"], "lang", str)
        config["path"]["lang"] = str(
            Path(replace_path_alias(config["path"]["lang"])).resolve()
        )

        return True

    if is_complete_config(config):
        return config
    raise RuntimeError


def read_local_auth(auth_path: str) -> AuthConfig:
    """Reads the local auth file from the specified path."""
    logger.debug("Reading local auth config %s", {"path": auth_path})
    with open(auth_path, "r", encoding="utf-8") as auth_file:
        auth = cast(Dict[str, Any], tomlkit.parse(auth_file.read()))
        logger.debug("Found auth config file")

    # Merge local keys with any external keys
    for index, external_source in enumerate(auth.pop("external", [])):
        logger.debug("Supplementing auth config with external secrets")
        logger.debug(
            "Fetching secret %s",
            {"index": index, "secret_name": external_source["secret_name"]},
        )
        if external_source["source"] != "AWSSecretsManager":
            raise ValueError(
                "External auth other than AWSSecretsManager not supported"
            )
        auth.update(
            AWS.get_secrets(
                external_source["region_name"],
                external_source["secret_name"],
                external_source["use_keys"],
            )
        )
        logger.debug("Supplemented secret %s", {"index": index})

    def is_complete_auth(auth: Dict[str, Any]) -> TypeGuard[AuthConfig]:
        assert_key = assert_key_for_scope("authentication file")

        assert_key(auth, "wikidot_password", str)
        assert_key(auth, "gmail_password", str)
        assert_key(auth, "mysql_host", str)
        assert_key(auth, "mysql_username", str)
        assert_key(auth, "mysql_password", str)

        return True

    if is_complete_auth(auth):
        return auth
    raise RuntimeError
