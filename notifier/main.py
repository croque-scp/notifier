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
from notifier.timing import delay, now, override_current_time
from notifier.types import AuthConfig, LocalConfig

logger = logging.getLogger(__name__)


def main(
    *,
    config: LocalConfig,
    auth: AuthConfig,
    execute_now: List[str] = None,
    limit_wikis: List[str] = None,
    force_initial_search_timestamp: int = None,
    force_current_time: str = None,
    dry_run=False,
):
    """Main notifier application entrypoint."""

    logger.info("The current time is %s", now)

    if force_current_time is not None:
        override_current_time(force_current_time)
        logger.info("The current time is %s", now)

    if dry_run:
        logger.info("Performing a dry run - no notifications will be sent")
    else:
        logger.info(
            "Not performing a dry run - cancel within 5s if not intended"
        )
        delay()

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
        logger.info("execute_now not present. Starting in scheduled mode")

        # Scheduler is responsible for executing tasks at the right times
        scheduler = BlockingScheduler()

        # Schedule the task
        scheduler.add_job(
            lambda: notify(
                config=config,
                auth=auth,
                active_channels=pick_channels_to_notify(),
                database=database,
                limit_wikis=limit_wikis,
                force_initial_search_timestamp=force_initial_search_timestamp,
                dry_run=dry_run,
            ),
            CronTrigger.from_crontab(notification_channels["hourly"]),
        )

        # Start the service
        scheduler.start()
    else:
        logger.info(
            "execute_now list provided. Starting in instant execution mode"
        )

        # Choose which channels to activate
        channels = pick_channels_to_notify(execute_now)

        # Run immediately and once only
        notify(
            config=config,
            auth=auth,
            active_channels=channels,
            database=database,
            limit_wikis=limit_wikis,
            force_initial_search_timestamp=force_initial_search_timestamp,
            dry_run=dry_run,
        )

        print("Finished")
