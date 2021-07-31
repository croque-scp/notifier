from typing import Dict, List, Literal, Optional, TypedDict, Union

IsSecure = Union[Literal[0], Literal[1]]


class LocalConfig(TypedDict):
    """Contents of the local config file."""

    wikidot_username: str
    config_wiki: str
    user_config_category: str
    wiki_config_category: str
    overrides_url: str


class SupportedWikiConfig(TypedDict):
    """A single remote wiki config."""

    id: str
    secure: IsSecure


class GlobalOverrideConfig(TypedDict):
    """A single remote override config."""

    description: str
    action: str
    category_id_is: Optional[str]
    thread_id_is: Optional[str]
    thread_title_matches: Optional[str]


# A collection of remote override configs, keyed by wiki.
GlobalOverridesConfig = Dict[str, List[GlobalOverrideConfig]]

# Direction of a subscription (-1 indicates an unsubscription).
SubscriptionCardinality = Union[Literal[-1], Literal[1]]


class Subscription(TypedDict):
    """A user's (un)subscription to a single thread or post."""

    thread_id: str
    post_id: Optional[str]
    sub: SubscriptionCardinality


class UserConfig(TypedDict):
    """A single remote user config."""

    user_id: str
    username: str
    frequency: str
    language: str
    subscriptions: List[Subscription]
    unsubscriptions: List[Subscription]


class PostInfo(TypedDict):
    """Information for a single post returned from the cache."""

    id: str
    title: str
    username: str
    posted_timestamp: int
    thread_id: str
    thread_title: str
    wiki_id: str
    wiki_secure: IsSecure


class ThreadPostInfo(PostInfo):
    """Information for a new post made to a thread from the cache."""


class PostReplyInfo(PostInfo):
    """Information for a new reply to a post from the cache."""

    parent_post_id: Union[str, None]
    parent_title: Union[str, None]


class NewPostsInfo(TypedDict):
    """All new posts returned from the cache."""

    thread_posts: List[ThreadPostInfo]
    post_replies: List[PostReplyInfo]
