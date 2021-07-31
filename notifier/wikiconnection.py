from typing import Generator, Iterable, cast

import requests
from bs4 import BeautifulSoup
from bs4.element import PageElement

listpages_div_class = "listpages-div-wrap"

listpages_div_wrap = f"""
[[div_ class="{listpages_div_class}"]]
{{}}
[[/div]]
"""


class Connection:
    """Connection to Wikidot facilitating communications with it."""

    def __init__(self, username, password):
        """Connect to Wikidot."""
        self._session = requests.sessions.Session()
        self.username = username
        self.password = password
        self.login()

    def module(self, wiki, module, **kwargs):
        """Call a Wikidot module."""
        response = self.post(
            "http://{}.wikidot.com/ajax-module-connector.php".format(wiki),
            data=dict(moduleName=module, wikidot_token7="123456", **kwargs),
            cookies={"wikidot_token7": "123456"},
        ).json()
        if response["status"] != "ok":
            raise RuntimeError(response.get("message") or response["status"])
        return response

    def listpages(
        self, wiki: str, *, module_body: str, **kwargs
    ) -> Generator[BeautifulSoup, None, None]:
        """Execute a ListPages search against a wiki and return all results
        as soup."""
        module_body = listpages_div_wrap.format(module_body)
        items = (
            soup
            for page in self.paginated_module(
                wiki,
                "list/ListPagesModule",
                index_key="offset",
                index_key_increment=250,
                perPage=250,
                module_body=module_body,
                **kwargs,
            )
            for soup in cast(
                Iterable[BeautifulSoup],
                BeautifulSoup(page["body"], "html.parser").find_all(
                    class_=listpages_div_class
                ),
            )
        )
        return items

    def paginated_module(
        self, wiki, module, index_key, index_key_increment=1, **kwargs
    ):
        """Generator that iterates pages of a paginated module response.

        :param wiki: The name of the wiki to query.
        :param module: The name of the module (which will return a
        paginated result) to query.
        :param index_key: The name of the parameter of this module that must be
        incrememented to access the next page.
        :param index_key_increment: The amount by which to increment the
        index key for each page.
        """
        first_page = self.module(wiki, module, **kwargs)
        yield first_page
        page_selectors = BeautifulSoup(first_page["body"], "html.parser").find(
            class_="pager"
        )
        if not page_selectors:
            return
        final_page_selector = page_selectors.select(
            ".target:nth-last-child(2)"
        )
        final_page_index = int(final_page_selector.a.string)
        for page_index in range(2, final_page_index + 1):
            kwargs.update({index_key: page_index * index_key_increment})
            yield self.module(wiki, module, **kwargs)

    def post(self, url, **kwargs):
        """Make a POST request."""
        return self._session.request("POST", url, **kwargs)

    def login(self):
        """Log in to a Wikidot account."""
        return self.post(
            "https://www.wikidot.com/default--flow/login__LoginPopupScreen",
            data=dict(
                login=self.username,
                password=self.password,
                action="Login2Action",
                event="login",
            ),
        )

    def get_new_posts(self, wiki):
        """Fetches information about new posts from a wiki's RSS."""
        # TODO
