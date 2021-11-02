import logging
from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from notifier.database.utils import resolve_driver_from_config
from notifier.notify import (
    notification_channels,
    notify,
    pick_channels_to_notify,
)
from notifier.timing import now
from notifier.types import AuthConfig, LocalConfig

logger = logging.getLogger(__name__)


def main(
    config: LocalConfig,
    auth: AuthConfig,
    execute_now: List[str] = None,
    limit_wikis: List[str] = None,
):
    """Main executor, supposed to be called via command line."""

    logger.info("The current time is %s", now)

    # Database stores forum posts and caches subscriptions
    DatabaseDriver = resolve_driver_from_config(config["database"]["driver"])
    database = DatabaseDriver(
        config["database"]["database_name"],
        host=auth["mysql_host"],
        username=auth["mysql_username"],
        password=auth["mysql_password"],
    )

    if limit_wikis is not None:
        logger.info("Wikis will be limited to %s", limit_wikis)

    if execute_now is None:
        logger.info("Starting in scheduled mode")

        # Scheduler is responsible for executing tasks at the right times
        scheduler = BlockingScheduler()

        # Schedule the task
        scheduler.add_job(
            lambda: notify(
                config, auth, pick_channels_to_notify(), database, limit_wikis
            ),
            CronTrigger.from_crontab(notification_channels["hourly"]),
        )

        # Start the service
        scheduler.start()
    else:
        logger.info("Starting in instant execution mode")

        # Choose which channels to activate
        channels = pick_channels_to_notify(execute_now)

        # Run immediately and once only
        notify(config, auth, channels, database, limit_wikis)

        print("Finished")
