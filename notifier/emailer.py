import yagmail

from notifier.types import LocalConfig


class Emailer:  # pylint: disable=too-few-public-methods
    """Responsible for sending emails."""

    def __init__(self, config: LocalConfig):
        self.yag = yagmail.SMTP(config["gmail_username"])

    def send(self, address: str, subject: str, body: str) -> None:
        """Send an email to an address."""
        self.yag.send(address, subject, body)
