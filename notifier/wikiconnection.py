from typing import Iterable, Iterator, List, Optional, Union, cast

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from notifier.parsethread import parse_thread_meta, parse_thread_page
from notifier.types import (
    EmailAddresses,
    LocalConfig,
    RawPost,
    RawThreadMeta,
    SupportedWikiConfig,
    WikidotResponse,
)

listpages_div_class = "listpages-div-wrap"

listpages_div_wrap = f"""
[[div_ class="{listpages_div_class}"]]
{{}}
[[/div]]
"""


class Connection:
    """Connection to Wikidot facilitating communications with it."""

    def __init__(
        self, config: LocalConfig, supported_wikis: List[SupportedWikiConfig]
    ):
        """Connect to Wikidot."""
        self._session = requests.sessions.Session()
        self.supported_wikis = supported_wikis
        # Always add the 'base' wiki, if it's not already present
        if not any(
            True for wiki in self.supported_wikis if wiki["id"] == "www"
        ):
            self.supported_wikis.append(
                {"id": "www", "name": "Wikidot", "secure": 1}
            )
        # Always add the configuration wiki, if it's not already present
        if not any(
            True
            for wiki in self.supported_wikis
            if wiki["id"] == config["config_wiki"]
        ):
            self.supported_wikis.append(
                {
                    "id": config["config_wiki"],
                    "name": "Configuration",
                    # Assume it's unsecure as that's most common
                    "secure": 0,
                }
            )

    def post(self, url, **kwargs):
        """Make a POST request."""
        return self._session.request("POST", url, **kwargs)

    def module(
        self, wiki_id: str, module_name: str, **kwargs
    ) -> WikidotResponse:
        """Call a Wikidot module."""
        # Check whether HTTP or HTTPS should be used for this wiki's AJAX
        # endpoint (HTTP-only wikis will reject HTTPS and vice versa,
        # though some wikis support both)
        secure = any(
            bool(wiki["secure"])
            for wiki in self.supported_wikis
            if wiki["id"] == wiki_id
        )
        # If we're logged in, grab the token7, otherwise make one up
        token7 = self._session.cookies.get("wikidot_token7", "7777777")
        response = self.post(
            "http{}://{}.wikidot.com/ajax-module-connector.php".format(
                "s" if secure else "", wiki_id
            ),
            data=dict(moduleName=module_name, wikidot_token7=token7, **kwargs),
            cookies={"wikidot_token7": token7},
        ).json()
        if response["status"] != "ok":
            print(response)
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
        :param starting_index: The initial value of the index. Usually 0
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

    def thread(
        self, wiki_id: str, thread_id: str, post_id: Optional[str] = None
    ) -> Iterator[Union[RawThreadMeta, RawPost]]:
        """Analyse a Wikidot thread.

        :param wiki_id: The ID of the wiki that contains the thread.
        :param thread_id: The ID of the thread.
        :param post_id: Either None, to get posts from the whole thread; or
        the ID of a post to focus on specifically.

        Returns an iterator.

        The first item of the iterator is information about the forum
        category that contains the thread; this takes the form of a tuple
        of category ID, category name, thread title. (The thread title may
        differ from the title of the first post.)

        All remaining items are posts. If post_id was provided, contains
        just the posts from the thread page that contains it (the first
        post might be the thread starter but probably isn't). Otherwise,
        contains all posts from the thread (the first post is the thread
        starter).
        """
        if post_id is None:
            thread_pages = (
                BeautifulSoup(page["body"], "html.parser")
                for page in self.paginated_module(
                    wiki_id,
                    "forum/ForumViewThreadModule",
                    index_key="pageNo",
                    starting_index=1,
                    t=thread_id,
                )
            )
            # I know that at least one page exists, so the call to `next` will
            # not raise a StopIteration
            # pylint: disable=stop-iteration-return
            first_page = next(thread_pages)
            yield parse_thread_meta(first_page)
            yield from parse_thread_page(thread_id, first_page)
            yield from (
                post
                for page in thread_pages
                for post in parse_thread_page(thread_id, page)
            )
        else:
            thread_page = BeautifulSoup(
                self.module(
                    wiki_id,
                    "forum/ForumViewThreadModule",
                    t=thread_id,
                    postId=post_id,
                )["body"],
                "html.parser",
            )
            yield parse_thread_meta(thread_page)
            yield from parse_thread_page(thread_id, thread_page)

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

    def get_contacts(self) -> EmailAddresses:
        """Get the account's contacts list and their emails in order to be
        able to send email notifications.

        Emails are personal information and are not cached to the database;
        they are discarded as soon as they're used.

        Connection needs to be logged in.
        """
        # TODO
