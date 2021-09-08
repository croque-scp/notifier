import sys

import keyring
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from notifier.config.local import read_local_config
from notifier.database.utils import resolve_driver_from_config
from notifier.notify import notification_channels, notify_active_channels
from notifier.types import LocalConfig


def read_command_line_arguments() -> str:
    """Extracts from the command line the required argument: the path to
    the config file.."""
    try:
        config_file_path = sys.argv[1]
    except IndexError as error:
        raise IndexError(
            "Argument (1) for config file location is required"
        ) from error
    try:
        read_local_config(config_file_path)
    except IOError as error:
        raise ValueError("Config file location is not readable") from error
    return config_file_path


def check_authentication(config: LocalConfig) -> None:
    """Verifies that the Wikidot and gmail passwords have been provided."""
    if not keyring.get_password("wikidot", config["wikidot_username"]):
        raise ValueError("Wikidot account password is not configured")
    if not keyring.get_password("yagmail", config["gmail_username"]):
        raise ValueError("gmail account password is not configured")


if __name__ == "__main__":
    # Get config location
    local_config_path = read_command_line_arguments()
    config = read_local_config(local_config_path)

    # Check that authentication has been set up
    check_authentication(read_local_config(local_config_path))

    # Scheduler is responsible for executing tasks at the right times
    scheduler = BlockingScheduler()

    # Database stores forum posts and caches subscriptions
    DatabaseDriver = resolve_driver_from_config(config["database_driver"])
    database = DatabaseDriver(config["database_name"])

    # Schedule the task
    scheduler.add_job(
        notify_active_channels,
        CronTrigger.from_crontab(notification_channels["hourly"]),
        args=(local_config_path, database),
    )

    # Let's go
    scheduler.start()
