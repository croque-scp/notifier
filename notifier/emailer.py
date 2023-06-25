import logging
from typing import cast

import yagmail

logger = logging.getLogger(__name__)


class Emailer:  # pylint: disable=too-few-public-methods
    """Responsible for sending emails."""

    def __init__(
        self,
        gmail_username: str,
        gmail_password: str,
        *,
        dry_run: bool = False,
    ):
        self.dry_run = dry_run
        if dry_run:
            self.yag = cast(yagmail.SMTP, object())
        else:
            self.yag = yagmail.SMTP(gmail_username, gmail_password)

    def send(self, address: str, subject: str, body: str) -> None:
        """Send an email to an address."""
        if self.dry_run:
            logger.warn("Dry run: email send was rejected")
            return
        self.yag.send(address, subject, body, prettify_html=False)
