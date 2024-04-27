import logging
import re
import time
from json import JSONDecodeError
from typing import (
    Any,
    Iterable,
    Iterator,
    List,
    Match,
    Optional,
    Tuple,
    Union,
    cast,
)

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from requests import Response

from notifier.parsethread import (
    count_pages,
    get_user_from_nametag,
    parse_thread_meta,
    parse_thread_page,
)
from notifier.types import (
    EmailAddresses,
    LocalConfig,
    RawPost,
    RawThreadMeta,
    SupportedWikiConfig,
    WikidotResponse,
)

logger = logging.getLogger(__name__)

listpages_div_class = "listpages-div-wrap"

listpages_div_wrap = f"""
[[div_ class="{listpages_div_class}"]]
{{}}
[[/div]]
"""


class ThreadNotExists(Exception):
    """Indicates that a thread does not exist, meaning (if it was known to
    exist before) that it was deleted."""


class RestrictedInbox(Exception):
    """Indicates that a user could not receive a Wikidot PM because their
    inbox is restricted."""


class NotLoggedIn(Exception):
    """Indicates that the client needs to be logged in to do that."""


class OngoingConnectionError(Exception):
    """Indicates a persistent connection error that could not be resolved
    by trying it multiple times."""


class Connection:
    """Connection to Wikidot facilitating communications with it."""

    PAGINATION_DELAY_S = 1.0
    MODULE_ATTEMPT_LIMIT = 3

    def __init__(
        self,
        config: LocalConfig,
        supported_wikis: List[SupportedWikiConfig],
        *,
        dry_run: bool = False,
    ):
        """Connect to Wikidot."""
        self.dry_run = dry_run
        if self.dry_run:
            # Theoretically the session will never be used in a dry run
            logger.info("Dry run: Wikidot requests will be rejected")
            self._session = cast(requests.sessions.Session, object())
        else:
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
        try:
            self.config_wiki = next(
                wiki
                for wiki in self.supported_wikis
                if wiki["id"] == config["config_wiki"]
            )
        except StopIteration:
            self.config_wiki = {
                "id": config["config_wiki"],
                "name": "Configuration",
                # Assume it's unsecure as that's most common
                "secure": 0,
            }
            self.supported_wikis.append(self.config_wiki)

    def post(self, url: str, **request_kwargs: Any) -> Response:
        """Make a POST request."""
        if self.dry_run:
            logger.warning(
                "Dry run: Wikidot request was not sent %s", {"to": url}
            )
            return Response()
        return self._session.request("POST", url, **request_kwargs)

    def module(
        self, wiki_id: str, module_name: str, **module_kwargs: Any
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
        token7 = self._session.cookies.get(  # type:ignore # there is a mistake in the stubs somewhere causing RequestsCookieJar.get to appear as dict.get
            "wikidot_token7", "7777777", domain=f"{wiki_id}.wikidot.com"
        )

        # Try the module a few times with increasing delay in case it fails
        for attempt_count in range(self.MODULE_ATTEMPT_LIMIT):
            attempt_delay = 2**attempt_count * self.PAGINATION_DELAY_S
            logger.debug(
                "Trying module connection %s",
                {
                    "attempt_number": attempt_count + 1,
                    "attempt_delay_s": attempt_delay,
                    "max_attempts": self.MODULE_ATTEMPT_LIMIT,
                },
            )
            time.sleep(attempt_delay)
            try:
                response_raw = self.post(
                    "http{}://{}.wikidot.com/ajax-module-connector.php".format(
                        "s" if secure else "", wiki_id
                    ),
                    data=dict(
                        moduleName=module_name,
                        wikidot_token7=token7,
                        **module_kwargs,
                    ),
                    cookies={"wikidot_token7": token7},
                )
                # Successful response, break to parsing
                break
            except ConnectionError as error:
                will_retry = attempt_count > self.MODULE_ATTEMPT_LIMIT
                logger.debug(
                    "Module connection failed %s",
                    {
                        "attempt_number": attempt_count + 1,
                        "attempt_delay_s": attempt_delay,
                        "max_attempts": self.MODULE_ATTEMPT_LIMIT,
                        "will_retry": will_retry,
                    },
                    exc_info=error,
                )
                if not will_retry:
                    raise OngoingConnectionError from error

        try:
            response = response_raw.json()
        except JSONDecodeError:
            logger.error(
                "Could not decode response %s",
                {
                    "wiki_id": wiki_id,
                    "secure": secure,
                    "module_name": module_name,
                    "module_kwargs": module_kwargs,
                    "status": response_raw.status_code,
                    "response_text": response_raw.text,
                },
            )
            raise
        if response["status"] == "no_thread":
            raise ThreadNotExists
        if (
            response["status"] == "no_permission"
            and response["message"]
            == "This user wishes to receive messages only from selected users."
        ):
            raise RestrictedInbox
        if (
            response["status"] == "no_permission"
            and response["message"]
            == "Please create a Wikidot account and/or sign in first"
        ):
            raise NotLoggedIn
        if response["status"] != "ok":
            logger.error(
                "Bad response from Wikidot %s",
                {
                    "wiki_id": wiki_id,
                    "secure": secure,
                    "module_name": module_name,
                    "module_kwargs": module_kwargs,
                    "response": response,
                },
            )
            raise RuntimeError(
                f"{response.get('message')} [{response['status']}]"
                if response.get("message")
                else response["status"]
            )
        return cast(WikidotResponse, response)

    def paginated_module(
        self,
        wiki: str,
        module_name: str,
        *,
        index_key: str,
        starting_index: int,
        index_increment: int = 1,
        **module_kwargs: Any,
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
        logger.debug(
            "Paginated module %s",
            {
                "index": module_kwargs.get(index_key, starting_index),
                "module_name": module_name,
                "wiki_id": wiki,
            },
        )
        first_page = self.module(wiki, module_name, **module_kwargs)
        yield first_page
        page_count, _ = count_pages(first_page["body"])
        # Iterate through the remaining pages
        # Start from the starting index plus one, because the first page
        # was already done
        # End at the final page plus one because range() is head exclusive
        # (this assumes that the index is 1-based)
        for page_index in range(starting_index + 1, page_count + 1):
            module_kwargs.update({index_key: page_index * index_increment})
            logger.debug(
                "Paginated module %s",
                {
                    "index": module_kwargs[index_key],
                    "module_name": module_name,
                    "wiki_id": wiki,
                },
            )
            yield self.module(wiki, module_name, **module_kwargs)

    def listpages(
        self, wiki_id: str, *, module_body: str, **module_kwargs: Any
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
                **module_kwargs,
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
        self,
        wiki_id: str,
        thread_id: str,
        containing_post_id: Optional[str] = None,
    ) -> Tuple[RawThreadMeta, List[RawPost]]:
        """Get posts from a page of a wiki thread.

        :param wiki_id: The ID of the wiki that contains the thread.
        :param thread_id: The ID of the thread.
        :param post_id: If provided, the thread page will be the one that contains this post; if not, the page will be the first in the thread.

        Returns a tuple with 2 items:

        1. Meta info about the thread.
        2. List of posts in this page of the thread.

        If no post with the given ID is in the thread, a null page is returned (i.e. the list of posts will be empty).
        """
        module_kwargs = {"t": thread_id.lstrip("t-")}
        if containing_post_id is not None:
            module_kwargs["postId"] = containing_post_id.lstrip("post-")

        thread_page = BeautifulSoup(
            self.module(
                wiki_id,
                "forum/ForumViewThreadModule",
                **module_kwargs,
            )["body"],
            "html.parser",
        )
        return (
            parse_thread_meta(thread_page),
            parse_thread_page(thread_id, thread_page),
        )

    def login(self, username: str, password: str) -> None:
        """Log in to a Wikidot account."""
        logger.info("Logging in...")
        response = self.post(
            "https://www.wikidot.com/default--flow/login__LoginPopupScreen",
            data=dict(
                login=username,
                password=password,
                action="Login2Action",
                event="login",
            ),
        )
        if "The login and password do not match" in response.text:
            raise RuntimeError("Failed to login")

    def send_message(self, user_id: str, subject: str, body: str) -> None:
        """Send a Wikidot message to the given user with the given subject
        and body.

        The Wikidot connection must be logged-in.
        """
        self.module(
            "www",
            "Empty",
            action="DashboardMessageAction",
            event="send",
            to_user_id=user_id,
            subject=subject,
            source=body,
        )

    def get_contacts(self) -> EmailAddresses:
        """Get the account's contacts list and their emails in order to be
        able to send email notifications.

        Emails are personal information and are not cached to the database;
        they are discarded as soon as they're used.

        Connection needs to be logged in.
        """
        contacts = BeautifulSoup(
            self.module("www", "dashboard/messages/DMContactsModule")["body"],
            "html.parser",
        )
        # Back contacts are stored in optional table.contact-list-table
        # which immediately follows h2 (there is an optional one
        # immediately following a h1 which is the regular contacts)
        back_contacts_heading = cast(Union[Tag, None], contacts.find("h2"))
        if back_contacts_heading is None:
            # The heading does not appear if there are no back contacts
            return {}
        back_contacts_table = cast(
            Union[Tag, None],
            back_contacts_heading.find_next_sibling(
                class_="contact-list-table"
            ),
        )
        if back_contacts_table is None:
            # If there is a heading there should also be a contacts table,
            # but can't hurt to be sure
            return {}
        addresses = {}
        for row in cast(Iterable[Tag], back_contacts_table.find_all("tr")):
            nametag_cell, address_cell = cast(
                Iterable[Tag], row.find_all("td")
            )
            _, username = get_user_from_nametag(
                cast(Tag, nametag_cell.find("span"))
            )
            if username is None:
                continue
            address = address_cell.get_text().strip()
            addresses[username.strip()] = address
        return addresses

    def get_page_id(self, wiki_id: str, slug: str) -> int:
        """Get a page's ID from its source."""
        try:
            wiki = next(
                wiki for wiki in self.supported_wikis if wiki["id"] == wiki_id
            )
        except StopIteration as error:
            raise RuntimeError(
                f"Cannot access page from unsupported wiki {wiki_id}"
            ) from error
        page_url = "http{}://{}.wikidot.com/{}".format(
            "s" if wiki["secure"] else "", wiki_id, slug
        )
        page = self._session.get(page_url).text
        return int(
            cast(Match[str], re.search(r"pageId = ([0-9]+);", page)).group(1)
        )

    def rename_page(self, wiki_id: str, from_slug: str, to_slug: str) -> None:
        """Renames a page.

        Renames can take a while (30+ seconds) to take effect, so if
        renaming for safe deletion, probably don't bother deleting until
        later.

        Connection needs to be logged in.
        """
        page_id = self.get_page_id(wiki_id, from_slug)
        logger.debug(
            "Renaming page %s",
            {
                "with id": page_id,
                "from slug": from_slug,
                "to slug": to_slug,
                "in wiki": wiki_id,
            },
        )
        self.module(
            wiki_id,
            "Empty",
            action="WikiPageAction",
            event="renamePage",
            page_id=str(page_id),
            new_name=to_slug,
        )

    def delete_page(self, wiki_id: str, slug: str) -> None:
        """Deletes a page.

        Connection needs to be logged in.
        """
        if not slug.startswith("deleted:"):
            raise RuntimeError(
                "Do not delete a page outside the deleted category"
                f" (rename it first) ({wiki_id}/{slug})"
            )
        page_id = self.get_page_id(wiki_id, slug)
        logger.debug(
            "Committing deletion of page %s",
            {
                "at slug": slug,
                "with id": page_id,
                "from wiki": wiki_id,
            },
        )
        self.module(
            wiki_id,
            "Empty",
            action="WikiPageAction",
            event="deletePage",
            page_id=str(page_id),
        )

    def set_tags(self, wiki_id: str, slug: str, tags: str) -> None:
        """Sets the tags on a page.

        Overrides all previous tags, so if amending a page's tags, be sure
        to have already observed them.

        Connection needs to be logged in.
        """
        page_id = self.get_page_id(wiki_id, slug)
        logger.debug(
            "Setting page tags %s",
            {
                "tags": tags,
                "on slug": slug,
                "with id": page_id,
                "on wiki": wiki_id,
            },
        )
        self.module(
            wiki_id,
            "Empty",
            action="WikiPageAction",
            event="saveTags",
            pageId=str(page_id),
            tags=tags.strip(),
        )
