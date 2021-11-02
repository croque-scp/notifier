import argparse
import logging
from typing import List, Optional, Tuple

from notifier.config.local import read_local_auth, read_local_config
from notifier.main import main
from notifier.notify import notification_channels
from notifier.types import AuthConfig, LocalConfig

logger = logging.getLogger(__name__)


def cli():
    """Run main procedure as a command-line tool."""
    config, auth, execute_now, limit_wikis = read_command_line_arguments()
    main(config, auth, execute_now, limit_wikis)


def read_command_line_arguments() -> Tuple[
    LocalConfig, AuthConfig, Optional[List[str]], Optional[List[str]]
]:
    """Extracts from the command line the config file and auth file."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config", type=str, help="Path to the main config file"
    )
    parser.add_argument(
        "auth", type=str, help="Path to the authentication config file"
    )
    parser.add_argument(
        "--execute-now",
        type=str,
        help="""A set of channel names to execute immediately, or none to
        determine automatically based on the current time.""",
        nargs="*",
        choices=notification_channels.keys(),
    )
    parser.add_argument(
        "--limit-wikis",
        type=str,
        help="""A set of wiki IDs to download new posts from. Must be a
        subset of the wiki IDs listed in the remote configuration.""",
        nargs="+",
    )
    args = parser.parse_args()

    config_file = read_local_config(args.config)
    auth_file = read_local_auth(args.auth)

    return config_file, auth_file, args.execute_now, args.limit_wikis
