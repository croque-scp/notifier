import argparse
import logging

from notifier.config.local import read_local_auth, read_local_config
from notifier.main import main
from notifier.notify import notification_channels

logger = logging.getLogger(__name__)


def cli() -> None:
    """Run main procedure as a command-line tool."""
    args = read_command_line_arguments()
    main(
        config=read_local_config(args.config),
        auth=read_local_auth(args.auth),
        execute_now=args.execute_now,
        limit_wikis=args.limit_wikis,
        force_initial_search_timestamp=args.force_initial_search_timestamp,
        dry_run=args.dry_run,
    )


def read_command_line_arguments() -> argparse.Namespace:
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
    parser.add_argument(
        "--force-initial-search-timestamp",
        type=int,
        help="""The lower timestamp to use when searching for posts.""",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="""A dry run will skip remote config acquisition, new post
        acquisition, and will not actually send any notifications.""",
    )

    return parser.parse_args()
