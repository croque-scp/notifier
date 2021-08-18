import time
from abc import ABC
from typing import List, Type, cast

import pycron

from notifier.config.tool import get_global_config, read_local_config
from notifier.config.user import get_user_config
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.digest import Digester
from notifier.newposts import get_new_posts
from notifier.types import EmailAddresses, PostInfo
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

    def notify(  # pylint: disable=too-many-arguments
        self,
        database: BaseDatabaseDriver,
        connection: Connection,
        digester: Digester,
        addresses: EmailAddresses,
        current_timestamp: int,
    ):
        """Execute this task's responsibilities."""
        print(f"Executing {self.frequency} notification channel")
        # Get config sans subscriptions for users who would be notified
        user_configs = database.get_user_configs(self.frequency)
        print(f"{len(user_configs)} users for {self.frequency} channel")
        # Notify each user on this frequency channel
        for user in user_configs:
            # Get new posts for this user
            posts = database.get_new_posts_for_user(
                user["user_id"],
                (user["last_notified_timestamp"], current_timestamp),
            )
            # Extract the 'last notification time' that will be recorded -
            # it is the timestamp of the most recent post this user is
            # being notified about
            last_notified_timestamp = max(
                post["posted_timestamp"]
                for post in (
                    posts["thread_posts"]
                    + cast(List[PostInfo], posts["post_replies"])
                )
            )
            # Compile the digest
            count, subject, body = digester.for_user(user, posts)
            if count == 0:
                # Nothing to notify the user about
                continue
            # Send the digests via PM to PM-subscribed users
            if user["delivery"] == "pm":
                connection.send_message(user["username"], subject, body)
            # Send the digests via email to email-subscribed users
            if user["delivery"] == "email":
                try:
                    address = addresses[user["username"]]
                except KeyError:
                    # This user requested to be notified via email but
                    # hasn't added the notification account as a contact,
                    # meaning their email address is unknown
                    print(f"{user['username']} is not a back-contact")
                    # They'll have to fix this themselves
                    continue
                send_email(address, subject, body)
            # Immediately after sending the notification, record the user's
            # last notification time
            # Minimising the number of computations between these two
            # processes is essential
            database.store_user_last_notified(
                user["user_id"], last_notified_timestamp
            )


def execute_tasks(
    local_config_path: str, database: BaseDatabaseDriver, wikidot_password: str
):
    """Main task executor. Should be called as often as the most frequent
    notification digest.

    Performs actions that must be run for every set of notifications (i.e.
    getting data for new posts) and then triggers the relevant notification
    schedules.
    """
    # Check which notification channels should be activated
    active_channels: List[Type[NotificationChannel]] = [
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
    get_global_config(local_config, database, connection)
    get_user_config(local_config, database, connection)
    get_new_posts(database, connection)
    # Record the 'current' timestamp immediately after downloading posts
    current_timestamp = int(time.time())
    digester = Digester(local_config["path"]["lang"])
    connection.login(local_config["wikidot_username"], wikidot_password)
    # If there's at least one user subscribed via email, get the list of
    # emails from the notification account's back-contacts
    if database.check_would_email(
        [Channel.frequency for Channel in active_channels]
    ):
        addresses = connection.get_contacts()
    for Channel in active_channels:
        # Should this be asynchronous + parallel?
        Channel().notify(
            database, connection, digester, addresses, current_timestamp
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
