from abc import ABC
from datetime import datetime, timezone

import pycron

from notifier.config.tool import get_global_config, read_local_config
from notifier.config.user import get_user_config
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.wikiconnection import Connection


class NotificationChannel(ABC):
    """A scheduled notification for users on a specific frequency channel.

    :param database: The database to use for notifications.
    :param connection: Connection to Wikidot.

    :var crontab: Determines when each set of notifications should be sent
    out.
    """

    crontab = ""
    frequency = ""

    def notify(self, database: BaseDatabaseDriver, connection: Connection):
        """Execute this task's responsibilities."""


def execute_tasks(
    local_config_path: str,
    database: BaseDatabaseDriver,
):
    """Main task executor. Should be called as often as the most frequent
    notification digest.

    Performs actions that must be run for every set of notifications (i.e.
    getting data for new posts) and then triggers the relevant notification
    schedules.
    """
    # TODO This needs to happen *just before* posts are decached
    # TODO Move the below comment to where this value is stored
    # Store this value in the database to define the lower bound for the
    # next post search on this channel
    # I could just use the cron to derive the last time the channel
    # executed, but it wouldn't be precise and might cause duplication of
    # posts. Plus, if the tool missed notifying a channel, this causes it
    # to include all the posts that it would otherwise have forgotten
    post_search_upper_timestamp = int(
        datetime.now(tz=timezone.utc).timestamp()
    )
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
    connection = Connection()
    overrides, wikis = get_global_config(local_config, database, connection)
    user_config = get_user_config(local_config, database, connection)
    for Channel in active_channels:
        Channel(database, connection).notify(
            local_config, global_config, user_config
        )


class HourlyChannel(NotificationChannel):
    """Hourly notification channel."""

    crontab = "0 * * * *"
    frequency = "hourly"


class DailyChannel(NotificationChannel):
    """Hourly notification channel."""

    crontab = "0 0 * * *"
    frequency = "daily"


class WeeklyChannel(NotificationChannel):
    """Hourly notification channel."""

    crontab = "0 0 * * 0"
    frequency = "weekly"


class MonthlyChannel(NotificationChannel):
    """Hourly notification channel."""

    crontab = "0 0 1 * *"
    frequency = "monthly"
