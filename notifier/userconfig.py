from bs4 import BeautifulSoup
import tomlkit
from notifier.wikiconnection import Connection

# For ease of parsing, configurations are coerced to TOML format
listpages_body = '''
slug = "%%fullname%%"
username = "%%created_by_unix%%"
user_id = "%%created_by_id%%"
frequency = "%%form_raw{frequency}%%"
language = "%%form_raw{language}%%"
subscriptions = """
%%form_data{subscriptions}%%"""
unsubscriptions = """
%%form_data{unsubscriptions}%%"""
'''


def get_users(connection: Connection):
    """Gets a list of user configurations.

    User configurations are stored on the dedicated Wikidot site. They are
    cached in the SQLite database."""

    for page in connection.listpages(
        "tars",
        category="notify",
        order="updated_at desc",
        module_body=listpages_body,
    ):
        page = BeautifulSoup(page["body"], "html.parser")
        configs = page.find(class_="list-pages-box").find_all("p")
        for config in configs:
            try:
                config = tomlkit.parse(config.get_text())
            except:
                # If the parse fails, the user was probably trying code
                # injection or something - discard it
                continue
            category, slug = config["slug"].split(":")
            if category != "notify":
                continue
            if slug != config["username"]:
                # Only accept configs for the user who created the page
                continue
            # Store this config in the database
            pass
