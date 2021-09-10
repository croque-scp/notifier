from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Tuple

from notifier.types import (
    CachedUserConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
)


class BaseDatabaseDriver(ABC):
    """Base structure for the database driver which must be fulfilled by
    any implementations."""

    @abstractmethod
    def __init__(self, database_name: str):
        pass

    @abstractmethod
    def create_tables(self) -> None:
        """Initial setup for the database."""

    @abstractmethod
    def store_global_overrides(
        self, global_overrides: GlobalOverridesConfig
    ) -> None:
        """Store all global overrides, overwriting any that are already
        present."""

    @abstractmethod
    def get_global_overrides(self) -> GlobalOverridesConfig:
        """Gets all global overrides, keyed to the ID of the wiki they are
        set for."""

    @abstractmethod
    def find_new_threads(self, thread_ids: Iterable[str]) -> List[str]:
        """From a list of thread IDs, return those that are not already
        present in the cache."""

    @abstractmethod
    def mark_thread_as_deleted(self, thread_id: str) -> None:
        """Marks a thread as deleted, preventing its posts from appearing
        in notifications."""

    @abstractmethod
    def mark_post_as_deleted(self, post_id: str) -> None:
        """Marks a post as deleted, preventing it from appearing in
        notifications. Also mark its children as deleted, recursively."""

    @abstractmethod
    def get_new_posts_for_user(
        self, user_id: str, timestamp_range: Tuple[int, int]
    ) -> NewPostsInfo:
        """Get new posts for the users with the given ID made during the
        given time range.

        Returns a dict containing the thread posts and the post replies.
        """

    @abstractmethod
    def get_user_configs(self, frequency: str) -> List[CachedUserConfig]:
        """Get the cached config for users subscribed to the given channel
        frequency.

        The cached config also includes information about the user's
        subscriptions both manual and automatic.
        """

    @abstractmethod
    def store_user_configs(self, user_configs: List[RawUserConfig]) -> None:
        """Caches user notification configurations.

        :param user_configs: List of configurations for all users.
        """

    @abstractmethod
    def store_manual_sub(
        self, user_id: str, subscription: Subscription
    ) -> None:
        """Caches a single user subscription configuration.

        :param user_id: The numeric Wikidot ID of the user, as text.
        :param thread_id: Data for the subscription.
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
    def store_thread(
        self,
        wiki_id: str,
        category: Tuple[Optional[str], Optional[str]],
        thread: Tuple[str, str, Optional[str], int],
    ) -> None:
        """Store a thread. Doesn't matter if the thread or category is
        already known or not.

        :param wiki_id: The ID of the wiki that contains the thread.
        :param thread: A tuple containing information about the thread: ID,
        title, creator username, and created timestamp.
        :param category: A tuple containing the ID and name of the category.
        """

    @abstractmethod
    def store_post(self, post: RawPost) -> None:
        """Store a post."""
