from abc import ABC, abstractmethod
from apscheduler.triggers.cron import CronTrigger


class ScheduledTask(ABC):
    crontab = None

    @property
    def trigger(self):
        return CronTrigger.from_crontab(self.crontab)

    @abstractmethod
    def execute(self):
        pass


class Hourly(ScheduledTask):
    crontab = "0 * * * *"

    def execute(self):
        get_new_posts()
        users = get_users()


class Daily(ScheduledTask):
    crontab = "0 0 * * *"

    def execute(self):
        users = get_users()


class Weekly(ScheduledTask):
    crontab = "0 0 * * 0"

    def execute(self):
        users = get_users()


class Monthly(ScheduledTask):
    crontab = "0 0 1 * *"

    def execute(self):
        users = get_users()
