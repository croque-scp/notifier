import re
from typing import Iterable

from notifier.types import (
    GlobalOverrideConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
    PostInfo,
    Subscription,
)


def apply_overrides(
    posts: NewPostsInfo,
    overrides: GlobalOverridesConfig,
    subscriptions: Iterable[Subscription],
) -> None:
    """Apply global overrides to a set of notifications.

    Modifies notifications in-place.

    :param posts: The group of notifications to modify.
    :param overrides: Overrides to apply to the notifications, potentially
    muting (i.e. removing) them.
    :param subscriptions: A user's manual subscriptions, which unlike the
    name suggests, can be used to override an override.
    """
    subs, unsubs = [], []
    for subscription in subscriptions:
        if subscription["sub"]:
            subs.append(subscription)
        else:
            unsubs.append(subscription)

    posts["thread_posts"] = [
        post
        for post in posts["thread_posts"]
        if not mutes_notification(
            post, overrides, subs, unsubs, is_reply=False
        )
    ]
    posts["post_replies"] = [
        reply
        for reply in posts["post_replies"]
        if not mutes_notification(
            reply, overrides, subs, unsubs, is_reply=True
        )
    ]


def mutes_notification(
    post: PostInfo,
    overrides: GlobalOverridesConfig,
    subs: Iterable[Subscription],
    unsubs: Iterable[Subscription],
    *,
    is_reply: bool,
) -> bool:
    """Determines whether a notification should be muted, based on the
    global overrides and a user's subscriptions."""
    # Always mute a post if the user is manually unsubscribed from it
    if any_subscription_applies_to_post(unsubs, post):
        return True
    # Never mute a post if the user is manually subscribed to it
    if any_subscription_applies_to_post(subs, post):
        return False
    # Otherwise, defer to overrides
    if any_override_mutes_post(post, overrides, is_reply):
        return True
    # If no overrides apply, permit the notification
    return False


def any_override_mutes_post(
    post: PostInfo, overrides: GlobalOverridesConfig, is_reply: bool
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


def any_subscription_applies_to_post(
    subscriptions: Iterable[Subscription], post: PostInfo
) -> bool:
    "Determines whether any of a user's subscriptions apply to a post."
    return any(
        subscription_applies_to_post(subscription, post)
        for subscription in subscriptions
    )


def subscription_applies_to_post(
    subscription: Subscription, post: PostInfo
) -> bool:
    """Determines whether a user subscription applies to a post.

    Does not check the cardinality of the subscription.
    """
    if subscription["thread_id"] != post["thread_id"]:
        return False
    return subscription["post_id"] == post["id"]
