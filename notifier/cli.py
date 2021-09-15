import argparse
import logging
from typing import List, Optional, Tuple

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from notifier.config.local import read_local_auth, read_local_config
from notifier.database.utils import resolve_driver_from_config
from notifier.notify import (
    notification_channels,
    notify,
    pick_channels_to_notify,
)
from notifier.types import AuthConfig, LocalConfig

logger = logging.getLogger(__name__)


def cli():
    """Run main procedure as a command-line tool."""
    # Get config location
    config, auth, execute_now = read_command_line_arguments()

    # Scheduler is responsible for executing tasks at the right times
    scheduler = BlockingScheduler()

    # Database stores forum posts and caches subscriptions
    DatabaseDriver = resolve_driver_from_config(config["database"]["driver"])
    database = DatabaseDriver(
        config["database"]["database_name"],
        host=auth["mysql_host"],
        username=auth["mysql_username"],
        password=auth["mysql_password"],
    )

    if execute_now is None:
        # Schedule the task
        scheduler.add_job(
            lambda: notify(config, auth, pick_channels_to_notify(), database),
            CronTrigger.from_crontab(notification_channels["hourly"]),
        )

        # Start the service
        scheduler.start()
    else:
        # Choose which channels to activate
        channels = pick_channels_to_notify(execute_now)

        # Run immediately and once only
        notify(config, auth, channels, database)

        print("Finished")


def read_command_line_arguments() -> Tuple[
    LocalConfig, AuthConfig, Optional[List[str]]
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
    args = parser.parse_args()

    config_file = read_local_config(args.config)
    auth_file = read_local_auth(args.auth)

    return config_file, auth_file, args.execute_now
