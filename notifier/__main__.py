import sys
from typing import Tuple

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from notifier.config.tool import read_local_config
from notifier.database.drivers import DatabaseDriver
from notifier.tasks import notification_channels, notify_active_channels


def read_command_line_arguments() -> Tuple[str, str]:
    """Extracts from the command line two required arguments; the path to
    the config file, and the notifier Wikidot account password."""
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
    try:
        wikidot_password = sys.argv[2]
    except IndexError as error:
        raise IndexError(
            "Argument (2) for account Wikidot password is required"
        ) from error
    return config_file_path, wikidot_password


if __name__ == "__main__":
    # Get config location and password
    local_config_path, wikidot_password = read_command_line_arguments()

    # Scheduler is responsible for executing tasks at the right times
    scheduler = BlockingScheduler()

    # Database stores forum posts and caches subscriptions
    database = DatabaseDriver("./postbox.db")

    # Schedule the task
    scheduler.add_job(
        notify_active_channels,
        CronTrigger.from_crontab(notification_channels["hourly"]),
        args=(local_config_path, database, wikidot_password),
    )

    # Let's go
    scheduler.start()
