from typing import Generator, Iterable, cast

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from notifier.types import WikidotResponse

listpages_div_class = "listpages-div-wrap"

listpages_div_wrap = f"""
[[div_ class="{listpages_div_class}"]]
{{}}
[[/div]]
"""


class Connection:
    """Connection to Wikidot facilitating communications with it."""

    def __init__(self):
        """Connect to Wikidot."""
        self._session = requests.sessions.Session()

    def post(self, url, **kwargs):
        """Make a POST request."""
        return self._session.request("POST", url, **kwargs)

    def module(self, wiki: str, module_name: str, **kwargs) -> WikidotResponse:
        """Call a Wikidot module."""
        response = self.post(
            "http://{}.wikidot.com/ajax-module-connector.php".format(wiki),
            data=dict(
                moduleName=module_name, wikidot_token7="123456", **kwargs
            ),
            cookies={"wikidot_token7": "123456"},
        ).json()
        if response["status"] != "ok":
            raise RuntimeError(response.get("message") or response["status"])
        return response

    def paginated_module(
        self,
        wiki: str,
        module_name: str,
        *,
        index_key: str,
        starting_index: int,
        index_increment=1,
        **kwargs,
    ) -> Iterator[WikidotResponse]:
        """Generator that iterates pages of a paginated module response.

        :param wiki: The name of the wiki to query.
        :param module_name: The name of the module (which will return a
        paginated result) to query.
        :param index_key: The name of the parameter of this module that
        must be incrememented to access the next page - e.g. 'offset' for
        ListPages and 'pageNo' for some other modules.
        :param starting_index: The initial value of the index. Usuaally 0
        for ListPages and 1 for most other modules.
        :param index_increment: The amount by which to increment the index
        key for each page. 1 for the vast majority of modules; often equal
        to the perPage value for ListPages.
        """
        first_page = self.module(wiki, module_name, **kwargs)
        yield first_page
        page_selectors = cast(
            Tag,
            BeautifulSoup(first_page["body"], "html.parser").find(
                class_="pager"
            ),
        )
        if not page_selectors:
            # There are no page selectors if there is only one page
            return
        final_page_selector = cast(
            Tag,
            cast(Tag, page_selectors.select(".target:nth-last-child(2)")[0]).a,
        )
        final_page_index = int(final_page_selector.get_text())
        # Iterate through the remaining pages
        # Start from the starting index plus one, because the first page
        # was already done
        # End at the final page plus one because range() is head exclusive
        for page_index in range(starting_index + 1, final_page_index + 1):
            kwargs.update({index_key: page_index * index_increment})
            yield self.module(wiki, module_name, **kwargs)

    def listpages(
        self, wiki_id: str, *, module_body: str, **kwargs
    ) -> Iterable[Tag]:
        """Execute a ListPages search against a wiki and return all results
        as soup."""
        module_body = listpages_div_wrap.format(module_body)
        items = (
            soup
            for page in self.paginated_module(
                wiki_id,
                "list/ListPagesModule",
                index_key="offset",
                starting_index=0,
                index_increment=250,
                perPage=250,
                module_body=module_body,
                **kwargs,
            )
            for soup in cast(
                Iterable[Tag],
                BeautifulSoup(page["body"], "html.parser").find_all(
                    class_=listpages_div_class
                ),
            )
        )
        return items

    def login(self, username: str, password: str) -> None:
        """Log in to a Wikidot account."""
        print("Logging in...")
        self.post(
            "https://www.wikidot.com/default--flow/login__LoginPopupScreen",
            data=dict(
                login=username,
                password=password,
                action="Login2Action",
                event="login",
            ),
        )

    def get_new_posts(self, wiki):
        """Fetches information about new posts from a wiki's RSS."""
        # TODO

    def get_contacts(self):
        """Get the account's contacts list and their emails in order to be
        able to send email notifications.

        Emails are personal information and are not cached to the database;
        they are discarded as soon as they're used.

        Connection needs to be logged in.
        """
        # TODO
