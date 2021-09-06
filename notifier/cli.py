import argparse
import logging
from typing import Tuple

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from notifier.config.local import read_local_auth, read_local_config
from notifier.database.utils import resolve_driver_from_config
from notifier.notify import (
    notification_channels,
    notify,
    print_time_until_next,
)
from notifier.types import AuthConfig, LocalConfig

logger = logging.getLogger(__name__)


def cli():
    """Run main procedure as a command-line tool."""
    # Get config location
    config, auth = read_command_line_arguments()

    # Scheduler is responsible for executing tasks at the right times
    scheduler = BlockingScheduler()

    # Database stores forum posts and caches subscriptions
    DatabaseDriver = resolve_driver_from_config(config["database"]["driver"])
    database = DatabaseDriver(config["database"]["database_name"])

    # Schedule the task
    scheduler.add_job(
        notify,
        CronTrigger.from_crontab(notification_channels["hourly"]),
        args=(config, auth, database),
    )

    print_time_until_next()

    # Let's go
    scheduler.start()


def read_command_line_arguments() -> Tuple[LocalConfig, AuthConfig]:
    """Extracts from the command line the config file and auth file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str)
    parser.add_argument("auth", type=str)
    args = parser.parse_args()

    config_file = read_local_config(args.config)
    auth_file = read_local_auth(args.auth)

    return config_file, auth_file
