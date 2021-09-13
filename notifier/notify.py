import logging
import re
import time
from typing import Iterable, List, Optional, cast

from notifier.config.remote import get_global_config
from notifier.config.user import get_user_config
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.deletions import clear_deleted_posts
from notifier.digest import Digester
from notifier.emailer import Emailer
from notifier.newposts import get_new_posts
from notifier.timing import channel_is_now, channel_will_be_next
from notifier.types import (
    AuthConfig,
    EmailAddresses,
    GlobalOverrideConfig,
    GlobalOverridesConfig,
    LocalConfig,
    NewPostsInfo,
    PostInfo,
)
from notifier.wikiconnection import Connection

logger = logging.getLogger(__name__)

# Notification channels with frequency names mapping to the crontab of that
# frequency.
notification_channels = {
    "hourly": "0 * * * *",
    "daily": "0 0 * * *",
    "weekly": "0 0 * * 0",
    "monthly": "0 0 1 * *",
}


def pick_channels_to_notify(force_channels: List[str] = None) -> List[str]:
    """Choose a set of channels to notify.

    :param force_channels: A list of channels to activate; or None, in
    which case a set of channels will be picked based on the current time,
    with the expectation that this function is called in the first minute
    of the hour.
    """
    logger.info("Checking active channels...")
    if force_channels is None or len(force_channels) == 0:
        channels = [
            frequency
            for frequency, crontab in notification_channels.items()
            if channel_is_now(crontab)
        ]
        logger.info(
            "Activating channels based on current timestamp %s",
            {"count": len(channels), "channels": channels},
        )
    else:
        channels = [
            c for c in force_channels if c in notification_channels.keys()
        ]
        logger.info(
            "Activating channels chosen manually %s",
            {"count": len(channels), "channels": channels},
        )
    return channels


def notify(
    config: LocalConfig,
    auth: AuthConfig,
    active_channels: List[str],
    database: BaseDatabaseDriver,
):
    """Main task executor. Should be called as often as the most frequent
    notification digest.

    Performs actions that must be run for every set of notifications (i.e.
    getting data for new posts) and then triggers the relevant notification
    schedules.
    """
    # If there are no active channels, which shouldn't happen, there is
    # nothing to do
    if len(active_channels) == 0:
        logger.warning("No active channels; aborting")
        return

    connection = Connection(config, database.get_supported_wikis())

    logger.info("Getting remote config...")
    get_global_config(config, database, connection)
    logger.info("Getting user config...")
    get_user_config(config, database, connection)

    # Refresh the connection to add any newly-configured wikis
    connection = Connection(config, database.get_supported_wikis())

    logger.info("Getting new posts...")
    get_new_posts(database, connection)

    # Record the 'current' timestamp immediately after downloading posts
    current_timestamp = int(time.time())
    # Get the password from keyring for login
    wikidot_password = auth["wikidot"]["password"]
    connection.login(config["wikidot_username"], wikidot_password)

    logger.info("Notifying...")
    notify_active_channels(
        active_channels, current_timestamp, config, auth, database, connection
    )

    logger.info("Cleaning up...")
    # Notifications have been sent, so perform time-insensitive maintenance
    for frequency in ["weekly", "monthly"]:
        if channel_will_be_next(notification_channels[frequency]):
            clear_deleted_posts(frequency, database, connection)


def notify_active_channels(
    active_channels: Iterable[str],
    current_timestamp: int,
    config: LocalConfig,
    auth: AuthConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
):
    """Prepare and send notifications to all activated channels."""
    digester = Digester(config["path"]["lang"])
    emailer = Emailer(config["gmail_username"], auth["yagmail"]["password"])
    for channel in active_channels:
        # Should this be asynchronous + parallel?
        notify_channel(
            channel,
            current_timestamp,
            database=database,
            connection=connection,
            digester=digester,
            emailer=emailer,
        )


def notify_channel(
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
    logger.info("Activating channel %s", {"channel": channel})
    # Get config sans subscriptions for users who would be notified
    user_configs = database.get_user_configs(channel)
    logger.debug(
        "Found users for channel %s",
        {"user_count": len(user_configs), "channel": channel},
    )
    # Notify each user on this frequency channel
    notified_users = 0
    for user in user_configs:
        logger.debug(
            "Making digest for user %s",
            {
                **user,
                "manual_subs": len(user["manual_subs"]),
                "auto_subs": len(user["auto_subs"]),
            },
        )
        # Get new posts for this user
        posts = database.get_new_posts_for_user(
            user["user_id"],
            (user["last_notified_timestamp"] + 1, current_timestamp),
        )
        apply_overrides(posts, database.get_global_overrides())
        post_count = len(posts["thread_posts"]) + len(posts["post_replies"])
        logger.debug(
            "Found posts for notification %s",
            {
                "username": user["username"],
                "post_count": post_count,
                "channel": channel,
            },
        )
        if post_count == 0:
            # Nothing to notify this user about
            logger.debug(
                "Aborting notification %s",
                {
                    "user": user["username"],
                    "channel": channel,
                    "reason": "no posts",
                },
            )
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
            logger.debug(
                "Sending notification %s",
                {"user": user["username"], "via": "pm", "channel": channel},
            )
            connection.send_message(user["user_id"], subject, body)
        # Send the digests via email to email-subscribed users
        if user["delivery"] == "email":
            if addresses is None:
                # Only get the contacts when there is actually a user who
                # needs to be emailed
                logger.info("Retrieving email contacts")
                addresses = connection.get_contacts()
                logger.debug(
                    "Retrieved email contacts %s",
                    {"address_count": len(addresses)},
                )
            try:
                logger.debug("Using cached email contacts")
                address = addresses[user["username"]]
            except KeyError:
                # This user requested to be notified via email but
                # hasn't added the notification account as a contact,
                # meaning their email address is unknown
                logger.warning(
                    "Aborting notification %s",
                    {
                        "user": user["username"],
                        "channel": channel,
                        "reason": "not a back-contact",
                    },
                )
                # They'll have to fix this themselves
                continue
            logger.debug(
                "Sending notification %s",
                {"user": user["username"], "via": "email", "channel": channel},
            )
            emailer.send(address, subject, body)
        # Immediately after sending the notification, record the user's
        # last notification time
        # Minimising the number of computations between these two
        # processes is essential
        database.store_user_last_notified(
            user["user_id"], last_notified_timestamp
        )
        logger.debug(
            "Recorded notification %s",
            {
                "username": user["username"],
                "recorded_timestamp": last_notified_timestamp,
                "channel": channel,
            },
        )
        notified_users += 1
    logger.info(
        "Finished notifying channel %s",
        {"channel": channel, "users_notified_count": notified_users},
    )


def apply_overrides(
    posts: NewPostsInfo, overrides: GlobalOverridesConfig
) -> None:
    """Apply global overrides to a set of notifications.

    Modifies notifications in-place.
    """
    posts["thread_posts"] = [
        post
        for post in posts["thread_posts"]
        if not any_override_mutes_post(post, overrides, is_reply=False)
    ]
    posts["post_replies"] = [
        reply
        for reply in posts["post_replies"]
        if not any_override_mutes_post(reply, overrides, is_reply=True)
    ]


def any_override_mutes_post(
    post: PostInfo, overrides: GlobalOverridesConfig, *, is_reply: bool
) -> bool:
    """Determines whether any override in the configured overrides would
    result in muting a notification."""
    return any(
        override["action"] in (["mute"] + ["mute_thread"] * (not is_reply))
        and override_applies_to_post(post, override)
        for override in overrides.get(post["wiki_id"], [])
    )


def override_applies_to_post(
    post: PostInfo, override: GlobalOverrideConfig
) -> bool:
    """Determines whether a given override applies to the given post.

    It is up to the caller to decide what happens if an override applies.
    """
    # All conditions of the override must be true for the override to
    # apply. So, return False if any of them are false, and True otherwise.
    if "category_id_is" in override and isinstance(
        override["category_id_is"], str
    ):
        if override["category_id_is"] != post["category_id"]:
            return False
    if "thread_id_is" in override and isinstance(
        override["thread_id_is"], str
    ):
        if override["thread_id_is"] != post["thread_id"]:
            return False
    if "thread_title_matches" in override and isinstance(
        override["thread_title_matches"], str
    ):
        try:
            match = re.search(
                override["thread_title_matches"], post["thread_title"]
            )
        except re.error:
            match = None
        if not match:
            return False
    return True
