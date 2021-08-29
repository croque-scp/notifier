from datetime import datetime, timedelta

import pycron


def channel_is_now(crontab: str):
    """Checks if the given notification channel should be activated right
    now."""
    return pycron.is_now(crontab)


def channel_will_be_next(crontab: str):
    """Checks if the given notification channel will be activated on the
    next channel, in an hour."""
    return pycron.is_now(crontab, dt=datetime.now() + timedelta(hours=1))


def channel_was_previous(crontab: str):
    """Checks if the given notification channel was activated on the
    previous channel an hour ago (in theory)."""
    return pycron.is_now(crontab, dt=datetime.now() - timedelta(hours=1))
