import sys
from typing import Tuple

from apscheduler.schedulers.blocking import BlockingScheduler

from notifier.config.tool import read_local_config
from notifier.database import DatabaseDriver
from notifier.tasks import Daily, Hourly, Monthly, Weekly
from notifier.wikiconnection import Connection


def add_job(scheduler, Task, database):
    task = Task(database)
    return scheduler.add_job(task.execute, task.trigger)


def read_command_line_arguments() -> Tuple[str, str]:
    """Extracts from the command line two required arguments; the path to
    the config file, and the notifier Wikidot account password."""
    try:
        config_file_path = sys.argv[1]
    except IndexError:
        raise IndexError("Argument (1) for config file location is required")
    try:
        read_local_config(config_file_path)
    except IOError:
        raise ValueError("Config file location is not readable")
    try:
        wikidot_password = sys.argv[2]
    except IndexError:
        raise IndexError(
            "Argument (2) for account Wikidot password is required"
        )
    return config_file_path, wikidot_password


if __name__ == "__main__":
    # Scheduler is responsible for executing tasks at the right times
    scheduler = BlockingScheduler()

    # Database stores forum posts and caches subscriptions
    database = DatabaseDriver("./postbox.db")

    # Connection facilitates communications with Wikidot
    connection = Connection()

    hourly_job = add_job(scheduler, Hourly, database)
    daily_job = add_job(scheduler, Daily, database)
    weekly_job = add_job(scheduler, Weekly, database)
    monthly_job = add_job(scheduler, Monthly, database)

    scheduler.start()
