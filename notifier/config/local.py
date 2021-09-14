import re
from pathlib import Path
from typing import Any, cast

import tomlkit
from typing_extensions import TypeGuard

from notifier.config.remote import AWS
from notifier.database.utils import resolve_driver_from_config
from notifier.types import AuthConfig, LocalConfig


def assert_key_for_scope(scope: str):
    """Checks that a key of the given name and type is present in a config."""

    def assert_key(config: dict, key: str, instance: Any) -> None:
        if not isinstance(config.get(key), instance):
            raise KeyError(f"Missing {key} in {scope}")

    return assert_key


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

    def is_complete_config(config: dict) -> TypeGuard[LocalConfig]:
        """Check that the config contains all required keys."""
        assert_key = assert_key_for_scope("main config")
        # Main config
        assert_key(config, "wikidot_username", str)
        assert_key(config, "config_wiki", str)
        assert_key(config, "user_config_category", str)
        assert_key(config, "wiki_config_category", str)
        assert_key(config, "overrides_url", str)
        assert_key(config, "gmail_username", str)

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
        config["path"]["lang"] = replace_path_alias(config["path"]["lang"])

        return True

    if is_complete_config(config):
        return config
    raise RuntimeError


def read_local_auth(auth_path: str) -> AuthConfig:
    """Reads the local auth file from the specified path."""
    with open(auth_path, "r") as auth_file:
        auth = cast(dict, tomlkit.parse(auth_file.read()))

    # Merge local keys with any external keys
    for external_source in auth.pop("external", []):
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

    def is_complete_auth(auth: dict) -> TypeGuard[AuthConfig]:
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
