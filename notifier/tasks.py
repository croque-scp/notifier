from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import pycron

from notifier.config.tool import read_local_config
from notifier.database.driver import BaseDatabaseDriver
from notifier.wikiconnection import Connection


@dataclass
class NotificationChannel(ABC):
    """A scheduled notification for users on a specific frequency channel.

    :param database: The database to use for notifications.

    :var crontab: Determines when each set of notifications should be sent
    out.
    """

    database: BaseDatabaseDriver
    crontab = None

    @abstractmethod
    def execute(self):
        """Execute this task's responsibilities."""
        pass


def execute_tasks(
    local_config_path: str,
    database: BaseDatabaseDriver,
    connection: Connection,
):
    """Main task executor. Should be called as often as the most frequent
    notification digest.

    Performs actions that must be run for every set of notifications (i.e.
    getting data for new posts) and then triggers the relevant notification
    schedules.
    """
    post_search_upper_timestamp = datetime.now()
    # Check which notification channels should be activated
    active_channels = [
        Channel
        for Channel in [
            HourlyChannel,
            DailyChannel,
            WeeklyChannel,
            MonthlyChannel,
        ]
        if pycron.is_now(Channel.crontab)
    ]
    # If there are no active channels, which shouldn't happen, there is
    # nothing to do
    if len(active_channels) == 0:
        print("No active channels")
        return
    local_config = read_local_config(local_config_path)
    read_global_config()
    read_user_config()
    for Channel in active_channels:
        Channel(database).execute()


class HourlyChannel(NotificationChannel):
    crontab = "0 * * * *"

    def execute(self):
        pass


class DailyChannel(NotificationChannel):
    crontab = "0 0 * * *"

    def execute(self):
        pass


class WeeklyChannel(NotificationChannel):
    crontab = "0 0 * * 0"

    def execute(self):
        pass


class MonthlyChannel(NotificationChannel):
    crontab = "0 0 1 * *"

    def execute(self):
        pass
