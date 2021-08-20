import time
from typing import List, Optional, cast

import keyring
import pycron

from notifier.config.tool import get_global_config, read_local_config
from notifier.config.user import get_user_config
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.digest import Digester
from notifier.emailer import Emailer
from notifier.newposts import get_new_posts
from notifier.types import EmailAddresses, PostInfo
from notifier.wikiconnection import Connection

# Notification channels with frequency names mapping to the crontab of that
# frequency.
notification_channels = {
    "hourly": "0 * * * *",
    "daily": "0 0 * * *",
    "weekly": "0 0 * * 0",
    "monthly": "0 0 1 * *",
}


def notify_channel(  # pylint: disable=too-many-arguments
    channel: str,
    current_timestamp: int,
    *,
    database: BaseDatabaseDriver,
    connection: Connection,
    digester: Digester,
    emailer: Emailer,
    addresses: Optional[EmailAddresses] = None,
):
    """Execute this task's responsibilities."""
    print(f"Executing {channel} notification channel")
    # Get config sans subscriptions for users who would be notified
    user_configs = database.get_user_configs(channel)
    print(f"{len(user_configs)} users for {channel} channel")
    # Notify each user on this frequency channel
    for user in user_configs:
        # Get new posts for this user
        posts = database.get_new_posts_for_user(
            user["user_id"],
            (user["last_notified_timestamp"], current_timestamp),
        )
        post_count = len(posts["thread_posts"]) + len(posts["post_replies"])
        print(
            "[{}] Notifying {} about {} posts via {}".format(
                channel, user["username"], post_count, user["delivery"]
            )
        )
        if post_count == 0:
            # Nothing to notify this user about
            continue
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
        subject, body = digester.for_user(user, posts)
        # Send the digests via PM to PM-subscribed users
        if user["delivery"] == "pm":
            connection.send_message(user["user_id"], subject, body)
        # Send the digests via email to email-subscribed users
        if user["delivery"] == "email":
            if addresses is None:
                # Only get the contacts when there is actually a user who
                # needs to be emailed
                addresses = connection.get_contacts()
            try:
                address = addresses[user["username"]]
            except KeyError:
                # This user requested to be notified via email but
                # hasn't added the notification account as a contact,
                # meaning their email address is unknown
                print(f"{user['username']} is not a back-contact")
                # They'll have to fix this themselves
                continue
            emailer.send(address, subject, body)
        # Immediately after sending the notification, record the user's
        # last notification time
        # Minimising the number of computations between these two
        # processes is essential
        database.store_user_last_notified(
            user["user_id"], last_notified_timestamp
        )
    print(f"Notified {len(user_configs)} users in {channel} channel")


def notify_active_channels(
    local_config_path: str, database: BaseDatabaseDriver
):
    """Main task executor. Should be called as often as the most frequent
    notification digest.

    Performs actions that must be run for every set of notifications (i.e.
    getting data for new posts) and then triggers the relevant notification
    schedules.
    """
    # Check which notification channels should be activated
    active_channels = [
        frequency
        for frequency, crontab in notification_channels.items()
        if pycron.is_now(crontab)
    ]
    # If there are no active channels, which shouldn't happen, there is
    # nothing to do
    if len(active_channels) == 0:
        print("No active channels")
        return
    config = read_local_config(local_config_path)
    connection = Connection(config, database.get_supported_wikis())
    get_global_config(config, database, connection)
    get_user_config(config, database, connection)
    # Refresh the connection to add any newly-configured wikis
    connection = Connection(config, database.get_supported_wikis())
    get_new_posts(database, connection)
    # Record the 'current' timestamp immediately after downloading posts
    current_timestamp = int(time.time())
    # Get the password from keyring for login
    wikidot_password = keyring.get_password(
        "wikidot", config["wikidot_username"]
    )
    if not wikidot_password:
        raise ValueError("Wikidot password improperly configured")
    connection.login(config["wikidot_username"], wikidot_password)
    for channel in active_channels:
        # Should this be asynchronous + parallel?
        notify_channel(
            channel,
            current_timestamp,
            database=database,
            connection=connection,
            digester=Digester(config["path"]["lang"]),
            emailer=Emailer(config["gmail_username"]),
        )
