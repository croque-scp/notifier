from typing import TypedDict, Union, Literal, Optional, Dict, List


class LocalConfig(TypedDict):
    wikidot_username: str
    config_wiki: str
    user_config_category: str
    site_config_category: str
    overrides_url: str


class SupportedSiteConfig(TypedDict):
    id: str
    secure: Union[Literal[0], Literal[1]]


class GlobalOverrideConfig(TypedDict):
    description: str
    action: str
    category_id_is: Optional[str]
    thread_id_is: Optional[str]
    thread_title_matches: Optional[str]


GlobalOverridesConfig = Dict[str, List[GlobalOverrideConfig]]


class Subscription(TypedDict):
    thread_id: str
    post_id: Union[str, None]
    sub: Union[Literal[-1], Literal[1]]


class UserConfig(TypedDict):
    user_id: str
    username: str
    frequency: str
    language: str
    subscriptions: List[Subscription]
    unsubscriptions: List[Subscription]
