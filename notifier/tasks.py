from abc import ABC, abstractmethod
from dataclasses import dataclass

from apscheduler.triggers.cron import CronTrigger

from notifier.database import DatabaseDriver


@dataclass
class ScheduledTask(ABC):
    database: DatabaseDriver
    crontab = None

    @property
    def trigger(self):
        return CronTrigger.from_crontab(self.crontab)

    @abstractmethod
    def execute(self):
        pass


class Hourly(ScheduledTask):
    """The hourly task is responsible for updating user configurations,
    checking for new posts, getting and storing information about those
    posts, and then sending notifications to users on the hourly channel."""

    crontab = "0 * * * *"

    def execute(self):
        read_config()
        get_new_posts()
        users = get_users()


class Daily(ScheduledTask):
    """The daily task is responsible for sending notifications to users on
    the daily channel."""

    crontab = "0 0 * * *"

    def execute(self):
        users = get_users()


class Weekly(ScheduledTask):
    """The weekly task is responsible for sending notifications to users on
    the weekly channel and for backing up the database."""

    crontab = "0 0 * * 0"

    def execute(self):
        users = get_users()
        backup_database()


class Monthly(ScheduledTask):
    """The monthly task is responsible for sending notifications to users on
    the monthly channel."""

    crontab = "0 0 1 * *"

    def execute(self):
        users = get_users()
