import logging
import re
from typing import Iterable, List, Optional, Tuple, Union, cast

from bs4 import BeautifulSoup
from bs4.element import Tag

from notifier.types import RawPost, RawThreadMeta

logger = logging.getLogger(__name__)


def parse_thread_meta(thread: Tag) -> RawThreadMeta:
    """Parse the meta info of a thread to return forum category ID, category name, and thread title.

    :param thread: The thread, as soup. Expected to start at .forum-thread-box, which is what the ForumViewThreadModule returns.

    Information returned is independent of the thread page passed to this function, except the returned value will include the active page number.
    """
    breadcrumbs = cast(Tag, thread.find(class_="forum-breadcrumbs"))
    category_link = list(cast(Iterable[Tag], breadcrumbs.find_all("a")))[-1]
    match = re.search(r"c-[0-9]+", category_link.get_attribute_list("href")[0])
    if match:
        category_id: Optional[str] = match[0]
        category_name: Optional[str] = category_link.get_text()
    else:
        category_id = category_name = None
    statistics = cast(Tag, thread.find(class_="statistics"))
    creator_username = get_user_from_nametag(
        cast(Tag, statistics.find(class_="printuser"))
    )[1]
    created_timestamp = get_timestamp(statistics)
    if created_timestamp is None:
        raise ValueError("No timestamp for thread")
    page_count, current_page = count_pages(thread)
    return {
        "category_id": category_id,
        "category_name": category_name,
        "title": list(breadcrumbs.stripped_strings)[-1].strip(" »"),
        "creator_username": creator_username,
        "created_timestamp": created_timestamp,
        "page_count": page_count,
        "current_page": current_page,
    }


def parse_thread_page(thread_id: str, thread_page: Tag) -> List[RawPost]:
    """Parse a page of posts in a soupy thread to individual raw posts.

    :param thread_id: The ID of the thread.
    :param thread_page: A page of that thread, as soup. Expected to start
    at .thread-container-posts or higher.

    Returns a list of metadata for posts found in that thread including
    parental relationships. Posts that are invalid for any reason are
    discarded.
    """
    # Wikidot posts are stored in #fpc-000.post-container, and inside that
    # is #post-000.post, where '000' is the numeric ID of the post.
    # The .post-container also contains the containers for any posts that
    # are replies to that post.
    raw_posts: List[RawPost] = []
    # Find all posts containers in the thread
    post_containers = cast(
        Iterable[Tag], thread_page.find_all(class_="post-container")
    )
    for post_container in post_containers:
        parent_post_id = None
        post = None
        post_id = None
        author_id = None
        author_name = None
        post_title = None
        post_snippet = None

        try:
            parent_post_id = get_post_parent_id(post_container)
            # Move to the post itself, to avoid deep searches accidentally
            # hitting replies
            post = cast(Tag, post_container.find(class_="post"))
            post_id = post.get_attribute_list("id")[0]
            # The post author and timestamp are kept in a .info - jump here to
            # avoid accidentally picking up users and timestamps from the post
            # body
            post_info = cast(Tag, post.find(class_="info"))
            post_author_nametag = cast(Tag, post_info.find(class_="printuser"))
            author_id, author_name = get_user_from_nametag(post_author_nametag)

            # Handle deleted/anonymous users by setting their info to an empty
            # string, and deal with it down the line
            if author_id is None:
                author_id = ""
            if author_name is None:
                # Wikidot accepts 'Anonymous' as a null value to [[user]] syntax
                author_name = "Anonymous"

            posted_timestamp = get_timestamp(post_info)
            if posted_timestamp is None:
                logger.warning(
                    "Could not parse timestamp for post %s",
                    {
                        "thread_id": thread_id,
                        "post_id": post_id,
                        "reason": "could not parse timestamp",
                    },
                )
                # Set the timestamp to 0 so it will never appear in a
                # notification, however, it must still be recorded to preserve
                # parent post relationships
                posted_timestamp = 0

            post_title = (
                cast(Tag, post.find(class_="title")).get_text().strip()
            )
            post_snippet = make_post_snippet(post)
            raw_posts.append(
                {
                    "id": post_id,
                    "thread_id": thread_id,
                    "parent_post_id": parent_post_id,
                    "posted_timestamp": posted_timestamp,
                    "title": post_title,
                    "snippet": post_snippet,
                    "user_id": author_id,
                    "username": author_name,
                }
            )
        except Exception as error:
            logger.error(
                "Could not parse post %s",
                {
                    "thread_id": thread_id,
                    "post_id": post_id,
                    "parent_post_id": parent_post_id,
                    "author_id": author_id,
                    "author_name": author_name,
                    "title": post_title,
                    "snippet": post_snippet,
                    "post": post,
                },
                exc_info=error,
            )
            raise
    return raw_posts


def make_post_snippet(post: Tag) -> str:
    """Truncate a post's text contents to elicit a snippet."""
    contents = cast(Tag, post.find(class_="content")).get_text().strip()
    if len(contents) >= 80:
        contents = contents[:75].strip() + "..."
    return contents


def get_post_parent_id(post_container: Tag) -> Optional[str]:
    """Checks the parent element of a post to see if it's another post; if
    it is, returns that post's ID. Returns None if the checked post is not
    a reply.

    :param post_container: The container of the post to check (not the post
    itself).
    """
    # If the post container is inside another post container, the ID of
    # that container is the ID of the parent post
    parent_element = cast(Tag, post_container.parent)
    parent_post_id = None
    if "post-container" in parent_element.get_attribute_list("class"):
        parent_container_id = parent_element.get_attribute_list("id")[0]
        parent_post_id = "post-" + parent_container_id.lstrip("fpc-")
    return parent_post_id


def get_user_from_nametag(nametag: Tag) -> Tuple[Optional[str], Optional[str]]:
    """Extract a user ID and a username from a nametag.

    A nametag is a .printuser, normally seen as .printuser.avatarhover, but
    there are other possibilities:
    - .printuser.deleted represents a deleted user with an ID but no name
    - .printuser.anonymous for anonymous users with no ID but an IP
    - .printuser with contents "Wikidot" for attributions to system
    - .printuser for a user link without an avatar
    - .printuser.avatarhover can also be a guest account

    Returns a tuple of user ID, username; either of which may be None.
    """
    classes = nametag.get_attribute_list("class")
    if "avatarhover" in classes:
        user_id = None
        username = nametag.get_text()
        # Get user ID from JavaScript click event handler
        click_handler = cast(Tag, nametag.contents[0]).get_attribute_list(
            "onclick"
        )[0]
        if click_handler is not None:
            # Click handler is not present for guest accounts
            match = re.search(r"[0-9]+", click_handler)
            if match:
                # Real user
                user_id = match[0]
        else:
            # Guest account
            if username.endswith(suffix := " (guest)"):
                username = username[: -len(suffix)]
        return user_id, username
    if "deleted" in classes:
        return nametag.get_attribute_list("data-id")[0], None
    if "anonymous" in classes:
        return None, None
    if nametag.get_text() == "Wikidot":
        return None, "Wikidot"
    # I don't think Wikidot normally returns just straight .printuser for
    # actual users anywhere unless explicitly asked for via ListPages, so
    # will ignore that for now
    return None, None


def get_timestamp(element: Tag) -> Optional[int]:
    """Retrieves a Wikidot timestamp.

    Returns None if this fails, though I see no reason that it should.
    """
    post_date = cast(Tag, element.find(class_="odate"))
    try:
        posted_timestamp = [
            int(css_class.lstrip("time_"))
            for css_class in post_date.get_attribute_list("class")
            if css_class.startswith("time_")
        ][0]
    except (IndexError, ValueError):
        return None
    return posted_timestamp


def count_pages(module_result: Union[str, Tag]) -> Tuple[int, Optional[int]]:
    """Counts the pages in a Wikidot module and gets the current page.

    Takes the HTML (as text or soup) of the output of any module that can return with a pager, and reads the text of the last page button to get the page number. The current page is 1-indexed.

    If a pager is not present, the page count is assumed to be 1.
    It's possible that no page is marked as the current one (no idea what causes this, but I've seen it happen).

    This process only works for modules that return pagers of a fixed length (the only one that I know of that does not do this is page history).

    Returns a tuple of the number of pages and the current page.
    """
    if isinstance(module_result, str):
        module_result = BeautifulSoup(module_result, "html.parser")

    page_count = 1
    current_page = None

    page_selectors = cast(Optional[Tag], module_result.find(class_="pager"))
    # Note that there are no page selectors if there is only one page

    if page_selectors:
        current_selector = page_selectors.find(class_="current")
        if current_selector:
            try:
                current_page = int(current_selector.get_text())
            except ValueError:
                pass

        # The final page selector is the last one with numeric text. It may be .target (clickable) or .current (unclickable). Non-numeric text indicates e.g. a 'next' button
        for selector in reversed(page_selectors.contents):
            try:
                page_count = int(selector.get_text())
                break
            except ValueError:
                continue

    return page_count, current_page
