from contextlib import contextmanager
import logging
import re
from smtplib import SMTPAuthenticationError
from typing import FrozenSet, Iterable, Iterator, List, Optional, Set, Tuple

from notifier.config.remote import get_global_config
from notifier.config.user import get_user_config
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.deletions import (
    clear_deleted_posts,
    delete_prepared_invalid_user_pages,
    rename_invalid_user_config_pages,
)
from notifier.digest import Digester
from notifier.dumps import LogDumpCacher, record_activation_log
from notifier.emailer import Emailer
from notifier.newposts import get_new_posts
from notifier.timing import channel_is_now, timestamp
from notifier.types import (
    ActivationLogDump,
    AuthConfig,
    CachedUserConfig,
    ChannelLogDump,
    EmailAddresses,
    LocalConfig,
)
from notifier.wikidot import (
    Wikidot,
    NotLoggedIn,
    RestrictedInbox,
    BlockedInbox,
)

logger = logging.getLogger(__name__)

# Notification channels with frequency names mapping to the crontab of that
# frequency.
notification_channels = {
    "test": "x x x x x",  # pycron accepts this value but it never passes
    "monthly": "0 18 1 * *",
    "weekly": "0 16 * * 0",
    "daily": "0 14 * * *",
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
        channels = [c for c in force_channels if c in notification_channels]
        logger.info(
            "Activating channels chosen manually %s",
            {"count": len(channels), "channels": channels},
        )
    return channels


@contextmanager
def activation_log_dump_context(
    config: LocalConfig, database: BaseDatabaseDriver, dry_run: bool
) -> Iterator[LogDumpCacher]:
    """Creates a log dump context that ends the long if the wrapped process fails."""
    activation_log_dump = LogDumpCacher[ActivationLogDump](
        {"start_timestamp": timestamp()},
        database.store_activation_log_dump,
        dry_run,
    )
    try:
        yield activation_log_dump

    finally:
        # Even if the run failed, record the end timestamp and upload if possible
        activation_log_dump.update({"end_timestamp": timestamp()})

        if not dry_run:
            logger.info("Uploading log dumps...")
            record_activation_log(config, database)


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

    with activation_log_dump_context(
        config, database, dry_run
    ) as activation_log_dump:
        # If there are no active channels, which shouldn't happen, there is
        # nothing to do
        if len(active_channels) == 0:
            logger.warning("No active channels; aborting")
            return

        wikidot = Wikidot(database.get_supported_wikis(), dry_run=dry_run)

        activation_log_dump.update({"config_start_timestamp": timestamp()})
        if dry_run:
            logger.info("Dry run: skipping remote config acquisition")
        else:
            logger.info("Getting remote config...")
            get_global_config(config, database, wikidot)
            logger.info("Getting user config...")
            get_user_config(config, database, wikidot)

            # Refresh the connection to add any newly-configured wikis
            wikidot = Wikidot(database.get_supported_wikis())
        activation_log_dump.update({"config_end_timestamp": timestamp()})

        activation_log_dump.update({"getpost_start_timestamp": timestamp()})
        if dry_run:
            logger.info("Dry run: skipping new post acquisition")
        else:
            logger.info("Getting new posts...")
            get_new_posts(database, wikidot, limit_wikis)
        # The timestamp immediately after downloading posts will be used as the
        # upper bound of posts to notify users about
        activation_log_dump.update({"getpost_end_timestamp": timestamp()})

        if dry_run:
            logger.info("Dry run: skipping Wikidot login")
        else:
            wikidot.login(config["wikidot_username"], auth["wikidot_password"])

        activation_log_dump.update({"notify_start_timestamp": timestamp()})
        logger.info("Notifying...")
        notify_active_channels(
            active_channels,
            current_timestamp=activation_log_dump.data.get(
                "getpost_end_timestamp", timestamp()
            ),
            config=config,
            auth=auth,
            database=database,
            wikidot=wikidot,
            force_initial_search_timestamp=force_initial_search_timestamp,
            dry_run=dry_run,
        )
        activation_log_dump.update({"notify_end_timestamp": timestamp()})

        # Notifications have been sent, so perform time-insensitive maintenance

        if dry_run:
            logger.info("Dry run: skipping cleanup")
            return

        logger.info("Cleaning up...")

        logger.info("Removing non-notifiable posts...")
        database.delete_non_notifiable_posts()

        logger.info("Checking for deleted posts")
        clear_deleted_posts(database, wikidot)

        logger.info("Purging invalid user config pages...")
        delete_prepared_invalid_user_pages(config, wikidot)
        rename_invalid_user_config_pages(config, wikidot)


def notify_active_channels(
    active_channels: Iterable[str],
    *,
    current_timestamp: int,
    config: LocalConfig,
    auth: AuthConfig,
    database: BaseDatabaseDriver,
    wikidot: Wikidot,
    force_initial_search_timestamp: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Prepare and send notifications to all activated channels."""
    digester = Digester(config["path"]["lang"])
    emailer = Emailer(
        config["gmail_username"], auth["gmail_password"], dry_run=dry_run
    )
    for channel in active_channels:
        notify_channel(
            channel,
            current_timestamp=current_timestamp,
            force_initial_search_timestamp=force_initial_search_timestamp,
            config=config,
            database=database,
            wikidot=wikidot,
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
    wikidot: Wikidot,
    digester: Digester,
    emailer: Emailer,
    dry_run: bool = False,
) -> None:
    """Compiles and sends notifications for all users in a given channel."""
    logger.info("Activating channel %s", {"channel": channel})
    channel_start_timestamp = timestamp()

    channel_log_dump = LogDumpCacher[ChannelLogDump](
        {
            "channel": channel,
            "start_timestamp": channel_start_timestamp,
        },
        database.store_channel_log_dump,
        dry_run,
    )

    # Get config sans subscriptions for users who would be notified
    logger.debug(
        "Finding users for channel... %s",
        {"channel": channel},
    )
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
    notified_posts = 0
    addresses: EmailAddresses = {}
    for user in user_configs:
        try:
            sent, post_count = notify_user(
                user,
                channel=channel,
                current_timestamp=current_timestamp,
                force_initial_search_timestamp=force_initial_search_timestamp,
                config=config,
                database=database,
                wikidot=wikidot,
                digester=digester,
                emailer=emailer,
                addresses=addresses,
                dry_run=dry_run,
            )
            if sent:
                notified_users += 1
                notified_posts += post_count
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
        except NotLoggedIn as error:
            logger.error("Failed to notify anyone; not logged in")
            raise RuntimeError from error
        except Exception as error:
            logger.error(
                "Failed to notify user %s",
                {
                    "reason": repr(error),
                    "for user": user["username"],
                    "in channel": channel,
                    "user_config": user,
                },
                exc_info=error,
            )
            continue

    channel_log_dump.update(
        {"end_timestamp": timestamp(), "notified_user_count": notified_users}
    )

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
    wikidot: Wikidot,
    digester: Digester,
    emailer: Emailer,
    addresses: EmailAddresses,
    dry_run: bool = False,
) -> Tuple[bool, int]:
    """Compiles and sends a notification for a single user.

    Returns a tuple containing the following:
        1. a boolean indicating whether the notification was successful
        2. the number of posts notified about

    :param addresses: A dict of email addresses to use for sending emails
    to. Should be set to an empty dict initially; if this is the case, this
    function will populate it from the notifier's Wikidot account. This
    object must not be reassigned, only mutated.
    """
    logger.debug(
        "Making digest for user %s",
        {
            "manual_subs_count": len(user["manual_subs"]),
            **user,
        },
    )
    # Get new posts for this user
    posts = database.get_notifiable_posts_for_user(
        user["user_id"],
        (
            (user["last_notified_timestamp"] + 1)
            if force_initial_search_timestamp is None
            else force_initial_search_timestamp,
            current_timestamp,
        ),
    )
    post_count = len(posts)
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
        return False, 0

    # Extract the 'last notification time' that will be recorded -
    # it is the timestamp of the most recent post this user is
    # being notified about
    last_notified_timestamp = max(post["posted_timestamp"] for post in posts)

    # Compile the digest
    subject, body = digester.for_user(user, posts)

    if dry_run:
        logger.info(
            "Dry run: not sending or recording notification %s",
            {"for_user": user["username"]},
        )
        # Still return true to indicate that the user would have been notified
        return True, post_count

    error_tags = {"restricted-inbox", "not-a-back-contact"}

    def update_tags_for_user(
        old_tags: FrozenSet[str], new_tags: Set[str]
    ) -> None:
        if old_tags == new_tags:
            return
        new_tags_string = " ".join(map(str, new_tags))
        wikidot.set_tags(
            config["config_wiki"],
            f"{config['user_config_category']}:{str(user['user_id'])}",
            new_tags_string,
        )

    def add_error_tag_to_user(error_tag: str, waiting_count: int = 0) -> None:
        old_tags = frozenset(user["tags"].split(" "))
        new_tags = set(old_tags)

        new_tags.add(error_tag)

        # Replace any numeric tags with the new waiting count
        new_tags.difference_update(
            tag for tag in new_tags if re.match(r"^_[0-9]+$", tag)
        )
        new_tags.add(f"_{waiting_count}")

        update_tags_for_user(old_tags, new_tags)

    def remove_error_tags_from_user() -> None:
        old_tags = frozenset(user["tags"].split(" "))
        new_tags = set(old_tags)

        # Remove all error tags
        new_tags.difference_update(error_tags)

        # Remove any waiting count tags as there is no longer an error
        new_tags.difference_update(
            tag for tag in new_tags if re.match(r"^_[0-9]+$", tag)
        )

        update_tags_for_user(old_tags, new_tags)

    # Send the digests via PM to PM-subscribed users
    if user["delivery"] == "pm":
        logger.debug(
            "Sending notification %s",
            {"to user": user["username"], "via": "pm", "channel": channel},
        )
        try:
            wikidot.send_message(user["user_id"], subject, body)
        except RestrictedInbox:
            # If the inbox is restricted to contacts only, inform the user
            logger.debug(
                "Aborting notification %s",
                {
                    "for user": user["username"],
                    "in channel": channel,
                    "reason": "restricted Wikidot inbox",
                },
            )
            add_error_tag_to_user("restricted-inbox", post_count)
            return False, 0
        except BlockedInbox:
            # If the inbox is blocked to all users, inform the user
            logger.debug(
                "Aborting notification %s",
                {
                    "for user": user["username"],
                    "in channel": channel,
                    "reason": "blocked Wikidot inbox",
                },
            )
            add_error_tag_to_user("blocked-inbox", post_count)
            return False, 0
        # This user has fixed the above issue, so remove error tags
        remove_error_tags_from_user()

    # Send the digests via email to email-subscribed users
    if user["delivery"] == "email":
        if addresses == {}:
            # Only get the contacts when there is actually a user who
            # needs to be emailed
            logger.info("Retrieving email contacts")
            addresses.update(wikidot.get_contacts())
            logger.debug(
                "Retrieved email contacts %s",
                {"address_count": len(addresses)},
            )
        else:
            logger.debug("Using cached email contacts")

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
            add_error_tag_to_user("not-a-back-contact", post_count)
            return False, 0
        # This user has fixed the above issue, so remove error tags
        remove_error_tags_from_user()
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
        wikidot.set_tags(
            config["config_wiki"],
            ":".join([config["user_config_category"], user["user_id"]]),
            "",
        )

    return True, post_count
