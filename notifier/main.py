from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from notifier.database.utils import resolve_driver_from_config
from notifier.notify import (
    notification_channels,
    notify,
    pick_channels_to_notify,
)
from notifier.types import AuthConfig, LocalConfig


def main(config: LocalConfig, auth: AuthConfig, execute_now: List[str] = None):
    """Main executor, supposed to be called via command line."""

    # Database stores forum posts and caches subscriptions
    DatabaseDriver = resolve_driver_from_config(config["database"]["driver"])
    database = DatabaseDriver(
        config["database"]["database_name"],
        host=auth["mysql_host"],
        username=auth["mysql_username"],
        password=auth["mysql_password"],
    )

    if execute_now is None:
        # Scheduler is responsible for executing tasks at the right times
        scheduler = BlockingScheduler()

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
