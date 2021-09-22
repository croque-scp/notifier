from datetime import datetime, timedelta

import pycron

# Store the current time as soon as possible
now = datetime.now()


def channel_is_now(crontab: str):
    """Checks if the given notification channel should be activated right
    now."""
    return pycron.is_now(crontab, now)


def channel_will_be_next(crontab: str):
    """Checks if the given notification channel will be activated on the
    next channel, in an hour."""
    return pycron.is_now(crontab, now + timedelta(hours=1))


def channel_was_previous(crontab: str):
    """Checks if the given notification channel was activated on the
    previous channel an hour ago (in theory)."""
    return pycron.is_now(crontab, now - timedelta(hours=1))
