from datetime import datetime, timedelta
import logging
import time

import pycron

logger = logging.getLogger(__name__)

# Store the current time as soon as possible
now = datetime.now()


def override_current_time(time: str):
    """Overrides the current time with the given ISO 8601 string."""
    global now
    now = datetime.fromisoformat(time.replace("Z", "+00:00"))
    logger.info(f"Current time forcibly overridden with {time}")


def delay():
    """Pause for a moment."""
    time.sleep(5)


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
