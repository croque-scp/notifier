import logging
import time
from smtplib import SMTPAuthenticationError
from typing import Iterable, List, Optional, Any, cast

from notifier.config.remote import get_global_config
from notifier.config.user import get_user_config
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.deletions import (
    clear_deleted_posts,
    delete_prepared_invalid_user_pages,
    rename_invalid_user_config_pages,
)
from notifier.digest import Digester
from notifier.emailer import Emailer
from notifier.newposts import get_new_posts
from notifier.overrides import apply_overrides
from notifier.timing import channel_is_now, channel_will_be_next
from notifier.types import (
    AuthConfig,
    CachedUserConfig,
    EmailAddresses,
    LocalConfig,
    PostInfo,
)
from notifier.wikiconnection import Connection, RestrictedInbox

logger = logging.getLogger(__name__)

# Notification channels with frequency names mapping to the crontab of that
# frequency.
notification_channels = {
    "test": "x x x x x",  # pycron accepts this value but it never passes
    "monthly": "0 15 1 * *",
    "weekly": "0 14 * * 0",
    "daily": "0 13 * * *",
    "8hourly": "0 4,12,20 * * *",
    "hourly": "0 * * * *",
}


def pick_channels_to_notify(
    force_channels: Optional[List[str]] = None,
) -> List[str]:
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
    *,
    config: LocalConfig,
    auth: AuthConfig,
    active_channels: List[str],
    database: BaseDatabaseDriver,
    limit_wikis: Optional[List[str]] = None,
    force_initial_search_timestamp: Optional[int] = None,
    dry_run: bool = False,
) -> None:
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

    connection = Connection(
        config, database.get_supported_wikis(), dry_run=dry_run
    )

    if dry_run:
        logger.info("Dry run: skipping remote config acquisition")
    else:
        logger.info("Getting remote config...")
        get_global_config(config, database, connection)
        logger.info("Getting user config...")
        get_user_config(config, database, connection)

        # Refresh the connection to add any newly-configured wikis
        connection = Connection(config, database.get_supported_wikis())

    if dry_run:
        logger.info("Dry run: skipping new post acquisition")
    else:
        logger.info("Getting new posts...")
        get_new_posts(database, connection, limit_wikis)

    # Record the 'current' timestamp immediately after downloading posts
    current_timestamp = int(time.time())
    # Get the password from keyring for login
    wikidot_password = auth["wikidot_password"]

    if dry_run:
        logger.info("Dry run: skipping Wikidot login")
    else:
        connection.login(config["wikidot_username"], wikidot_password)

    logger.info("Notifying...")
    notify_active_channels(
        active_channels,
        current_timestamp=current_timestamp,
        config=config,
        auth=auth,
        database=database,
        connection=connection,
        force_initial_search_timestamp=force_initial_search_timestamp,
        dry_run=dry_run,
    )

    if dry_run:
        logger.info("Dry run: skipping cleanup")
        return

    # Notifications have been sent, so perform time-insensitive maintenance
    logger.info("Cleaning up...")

    for frequency in ["weekly", "monthly"]:
        if channel_will_be_next(notification_channels[frequency]):
            logger.info(
                "Checking for deleted posts %s", {"for channel": frequency}
            )
            clear_deleted_posts(frequency, database, connection)

    logger.info("Purging invalid user config pages")
    delete_prepared_invalid_user_pages(config, connection)
    rename_invalid_user_config_pages(config, connection)


def notify_active_channels(
    active_channels: Iterable[str],
    *,
    current_timestamp: int,
    config: LocalConfig,
    auth: AuthConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
    force_initial_search_timestamp: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Prepare and send notifications to all activated channels."""
    digester = Digester(config["path"]["lang"])
    emailer = Emailer(
        config["gmail_username"], auth["gmail_password"], dry_run=dry_run
    )
    for channel in active_channels:
        # Should this be asynchronous + parallel?
        notify_channel(
            channel,
            current_timestamp=current_timestamp,
            force_initial_search_timestamp=force_initial_search_timestamp,
            config=config,
            database=database,
            connection=connection,
            digester=digester,
            emailer=emailer,
            dry_run=dry_run,
        )


def notify_channel(
    channel: str,
    *,
    current_timestamp: int,
    force_initial_search_timestamp: Optional[int] = None,
    config: LocalConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
    digester: Digester,
    emailer: Emailer,
    dry_run: bool = False,
) -> None:
    """Compiles and sends notifications for all users in a given channel."""
    logger.info("Activating channel %s", {"channel": channel})
    # Get config sans subscriptions for users who would be notified
    user_configs = database.get_user_configs(channel)
    logger.debug(
        "Found users for channel %s",
        {"user_count": len(user_configs), "channel": channel},
    )
    # Filter the users only to those with notifications waiting
    logger.debug("Filtering users without notifications waiting...")
    user_count_pre_filter = len(user_configs)
    notifiable_user_ids = database.get_notifiable_users(channel)
    user_configs = [
        user for user in user_configs if user["user_id"] in notifiable_user_ids
    ]
    logger.debug(
        "Filtered users without notifications waiting %s",
        {
            "from_count": user_count_pre_filter,
            "to_count": len(user_configs),
            "removed_count": user_count_pre_filter - len(user_configs),
            "users_with_waiting_notifs_count": len(notifiable_user_ids),
        },
    )
    # Notify each user on this frequency channel
    notified_users = 0
    addresses: EmailAddresses = {}
    for user in user_configs:
        try:
            notified_users += notify_user(
                user,
                channel=channel,
                current_timestamp=current_timestamp,
                force_initial_search_timestamp=force_initial_search_timestamp,
                config=config,
                database=database,
                connection=connection,
                digester=digester,
                emailer=emailer,
                addresses=addresses,
                dry_run=dry_run,
            )
        except SMTPAuthenticationError as error:
            logger.error(
                "Failed to notify user via email %s",
                {
                    "reason": "Gmail authentication failed",
                    "for user": user["username"],
                    "in channel": channel,
                },
                exc_info=error,
            )
            continue
        except Exception as error:
            logger.error(
                "Failed to notify user %s",
                {
                    "reason": "unknown",
                    "for user": user["username"],
                    "in channel": channel,
                    "user_config": user,
                },
                exc_info=error,
            )
            continue
    logger.info(
        "Finished notifying channel %s",
        {"channel": channel, "users_notified_count": notified_users},
    )


def notify_user(
    user: CachedUserConfig,
    *,
    channel: str,
    current_timestamp: int,
    force_initial_search_timestamp: Optional[int] = None,
    config: LocalConfig,
    database: BaseDatabaseDriver,
    connection: Connection,
    digester: Digester,
    emailer: Emailer,
    addresses: EmailAddresses,
    dry_run: bool = False,
) -> int:
    """Compiles and sends a notification for a single user.

    Returns a boolean indicating whether the notification was successful.

    :param addresses: A dict of email addresses to use for sending emails
    to. Should be set to an empty dict initially; if this is the case, this
    function will populate it from the notifier's Wikidot account. This
    object must not be reassigned, only mutated.
    """
    logger.debug(
        "Making digest for user %s",
        {
            **cast(Any, user),
            "manual_subs": len(user["manual_subs"]),
            "auto_subs": len(user["auto_subs"]),
        },
    )
    # Get new posts for this user
    posts = database.get_new_posts_for_user(
        user["user_id"],
        (
            (user["last_notified_timestamp"] + 1)
            if force_initial_search_timestamp is None
            else force_initial_search_timestamp,
            current_timestamp,
        ),
    )
    apply_overrides(
        posts, database.get_global_overrides(), user["manual_subs"]
    )
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
            "Skipping notification %s",
            {
                "for user": user["username"],
                "in channel": channel,
                "reason": "no posts",
            },
        )
        return False

    # Extract the 'last notification time' that will be recorded -
    # it is the timestamp of the most recent post this user is
    # being notified about
    last_notified_timestamp = max(
        post["posted_timestamp"]
        for post in (
            posts["thread_posts"] + cast(List[PostInfo], posts["post_replies"])
        )
    )

    # Compile the digest
    subject, body = digester.for_user(user, posts)

    if dry_run:
        logger.info(
            "Dry run: not sending or recording notification %s",
            {"for_user": user["username"]},
        )
        # Still return true to indicate that the user would have been notified
        return True

    # Send the digests via PM to PM-subscribed users
    pm_inform_tag = "restricted-inbox"
    if user["delivery"] == "pm":
        logger.debug(
            "Sending notification %s",
            {"to user": user["username"], "via": "pm", "channel": channel},
        )
        try:
            connection.send_message(user["user_id"], subject, body)
        except RestrictedInbox:
            # If the inbox is restricted, inform the user
            logger.debug(
                "Aborting notification %s",
                {
                    "for user": user["username"],
                    "in channel": channel,
                    "reason": "restricted Wikidot inbox",
                },
            )
            if pm_inform_tag not in user["tags"]:
                connection.set_tags(
                    config["config_wiki"],
                    ":".join(
                        [config["user_config_category"], str(user["user_id"])]
                    ),
                    " ".join([user["tags"], pm_inform_tag]),
                )
            return False

    # Send the digests via email to email-subscribed users
    if user["delivery"] == "email":
        if addresses == {}:
            # Only get the contacts when there is actually a user who
            # needs to be emailed
            logger.info("Retrieving email contacts")
            addresses.update(connection.get_contacts())
            logger.debug(
                "Retrieved email contacts %s",
                {"address_count": len(addresses)},
            )
        else:
            logger.debug("Using cached email contacts")

        email_inform_tag = "not-a-back-contact"
        try:
            address = addresses[user["username"]]
        except KeyError:
            # This user requested to be notified via email but
            # hasn't added the notification account as a contact,
            # meaning their email address is unknown
            logger.debug(
                "Aborting notification %s",
                {
                    "for user": user["username"],
                    "in channel": channel,
                    "reason": "not a back-contact",
                },
            )
            # They'll have to fix this themselves - inform them
            if email_inform_tag not in user["tags"]:
                connection.set_tags(
                    config["config_wiki"],
                    ":".join(
                        [config["user_config_category"], str(user["user_id"])]
                    ),
                    " ".join([user["tags"], email_inform_tag]),
                )
            return False
        if email_inform_tag in user["tags"]:
            # This user has fixed the above issue, so remove the tag
            connection.set_tags(
                config["config_wiki"],
                ":".join(
                    [config["user_config_category"], str(user["user_id"])]
                ),
                user["tags"].replace(email_inform_tag, ""),
            )
        logger.debug(
            "Sending notification %s",
            {"user": user["username"], "via": "email", "channel": channel},
        )
        emailer.send(address, subject, body)

    # Immediately after sending the notification, record the user's
    # last notification time
    # Minimising the number of computations between these two
    # processes is essential
    database.store_user_last_notified(user["user_id"], last_notified_timestamp)
    logger.debug(
        "Recorded notification for user %s",
        {
            "username": user["username"],
            "recorded_timestamp": last_notified_timestamp,
            "channel": channel,
        },
    )

    # If the delivery was successful, remove any error tags
    if user["tags"] != "":
        connection.set_tags(
            config["config_wiki"],
            ":".join([config["user_config_category"], str(user["user_id"])]),
            "",
        )

    return True
