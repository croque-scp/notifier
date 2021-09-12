import yagmail


class Emailer:  # pylint: disable=too-few-public-methods
    """Responsible for sending emails."""

    def __init__(self, gmail_username: str, gmail_password: str):
        self.yag = yagmail.SMTP(gmail_username, gmail_password)

    def send(self, address: str, subject: str, body: str) -> None:
        """Send an email to an address."""
        self.yag.send(address, subject, body, prettify_html=False)
