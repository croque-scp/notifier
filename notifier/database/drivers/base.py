from abc import ABC, abstractmethod
from typing import Any, List, Tuple

from notifier.types import (
    ActivationLogDump,
    CachedUserConfig,
    ChannelLogDump,
    LogDump,
    NotifiablePost,
    PostInfo,
    PostMeta,
    RawUserConfig,
    SupportedWikiConfig,
    Context,
)


class BaseDatabaseDriver(ABC):
    """Base structure for the database driver which must be fulfilled by
    any implementations."""

    @abstractmethod
    def __init__(self, database_name: str, **kwargs: Any):
        """Sets up and connects to the database."""

    @abstractmethod
    def scrub_database(self) -> None:
        """Purges all information from the database. Should only ever be
        used to clear the test database."""

    @abstractmethod
    def apply_migrations(self) -> None:
        """Extract the current database migration version, and apply all
        subsequent migrations."""

    @abstractmethod
    def create_tables(self) -> None:
        """Initial setup for the database."""

    @abstractmethod
    def get_latest_post_timestamp(self, wiki_id: str) -> int:
        """Returns the timestamp of the latest stored post with the given wiki context."""

    @abstractmethod
    def get_notifiable_posts_for_user(
        self, user_id: str, timestamp_range: Tuple[int, int]
    ) -> List[PostInfo]:
        """Get new posts for the users with the given ID made during the
        given time range."""

    @abstractmethod
    def get_user_configs(self, frequency: str) -> List[CachedUserConfig]:
        """Get the cached config for users subscribed to the given channel
        frequency.

        The cached config also includes information about the user's
        subscriptions both manual and automatic.
        """

    @abstractmethod
    def count_user_configs(self) -> int:
        """Count the number of subscribed users."""

    @abstractmethod
    def get_notifiable_users(self, frequency: str) -> List[str]:
        """Get the list of IDs for users subscribed to the given channel
        frequency who have at least one notification waiting for them.
        """

    @abstractmethod
    def get_posts_to_check_for_deletion(
        self, timestamp: int
    ) -> List[PostMeta]:
        """Get a list of posts to check for having potentially been deleted.

        Timestamp is assumed to be time to check relative to.
        """

    @abstractmethod
    def store_user_configs(
        self,
        user_configs: List[RawUserConfig],
        *,
        overwrite_existing: bool = True,
    ) -> None:
        """Caches user notification configurations.

        :param user_configs: List of configurations for all users.
        :param overwrite_existing: Whether to overwrite the existing set of
        user configs. Default true. If false, will append.
        """

    @abstractmethod
    def store_user_last_notified(
        self, user_id: str, last_notified_timestamp: int
    ) -> None:
        """Store the time at which the user with the given ID was last
        notified.

        The time should be the time of the most recent post the user has
        been notified about, but must only be saved once the notification
        has actually been delivered.
        """

    @abstractmethod
    def get_supported_wikis(self) -> List[SupportedWikiConfig]:
        """Get a list of supported wikis."""

    @abstractmethod
    def store_supported_wikis(self, wikis: List[SupportedWikiConfig]) -> None:
        """Stores a set of supported wikis in the database, overwriting any
        that are already present."""

    @abstractmethod
    def store_latest_post_timestamp(
        self, wiki_id: str, timestamp: int
    ) -> None:
        """Stores the latest seen post timestamp for the given wiki."""

    @abstractmethod
    def store_post(self, post: NotifiablePost) -> None:
        """Store a post."""

    @abstractmethod
    def store_context_forum_category(
        self, context_forum_category: Context.ForumCategory
    ) -> None:
        """Store a forum category for context."""

    @abstractmethod
    def store_context_thread(self, context_thread: Context.Thread) -> None:
        """Store a thread for context."""

    @abstractmethod
    def store_context_parent_post(
        self, context_parent_post: Context.ParentPost
    ) -> None:
        """Store a parent post for context."""

    @abstractmethod
    def delete_post(self, post_id: str) -> None:
        """Delete a post."""

    @abstractmethod
    def delete_non_notifiable_posts(self) -> None:
        """Delete posts that will not emit notifications."""

    @abstractmethod
    def delete_context_thread(self, thread_id: str) -> None:
        """Delete posts with the given thread context."""

    @abstractmethod
    def store_channel_log_dump(self, log: ChannelLogDump) -> None:
        """Store a channel log dump."""

    @abstractmethod
    def store_activation_log_dump(self, log: ActivationLogDump) -> None:
        """Store an activation log dump."""

    @abstractmethod
    def get_log_dumps_since(self, timestamp_range: Tuple[int, int]) -> LogDump:
        """Retrieve log dumps stored in the time range."""
