"""Set of functions specifying everything about all feeds."""

import re
from typing import Iterable
import emoji
from .config import FEED_TERMS, GENERAL_FEEDS


def remove_links_from_post(post: str) -> str:
    """Remove all links from the text of a post.
    Modified from https://stackoverflow.com/questions/11331982/how-to-remove-any-url-within-a-string-in-python
    """
    return re.sub(r"https?:\/{2}\S+", "", post)


# The same as string.punctuation in the base library, except we want to keep hashtags and also add newline etc chars
# to the list of punctuation identifiers to remove
PUNCTUATION = list(r"""!"$%&'()*+,-./:;<=>?@[\]^_`{|}~""") + ["\n", "\r"]


def remove_punctuation_from_post(post: str) -> str:
    """Removes all punctuation from a post - EXCEPT hashtags! Also converts post to lowercase."""
    return "".join([x if x not in PUNCTUATION else " " for x in post.lower()])


def remove_emoji_from_post(post: str) -> str:
    return emoji.replace_emoji(post, replace="")


def cleaned_word_list(post: str) -> list:
    """Generates a list of all words in a post.

    Words include a space at the start AND end, like:
    ' #astro '
    ' space '
    meaning that matches against these strings must be to whole terms.
    """
    post = remove_links_from_post(post)
    post = remove_punctuation_from_post(post)
    post = remove_emoji_from_post(post)
    return [f" {word} " for word in post.split()]


FEED_TERMS_WITH_SPACES = dict()
for feed, terms in (FEED_TERMS | GENERAL_FEEDS).items():
    if terms is not None:
        FEED_TERMS_WITH_SPACES[feed] = {}
        FEED_TERMS_WITH_SPACES[feed]["emoji"] = terms["emoji"]
        FEED_TERMS_WITH_SPACES[feed]["words"] = [f" {term} " for term in terms["words"]]
    else:
        FEED_TERMS_WITH_SPACES[feed] = None


def label_post(labels, post, words, feed, database_feed_prefix: str = "feed_"):
    """Labels a post as being in a given feed."""
    terms = FEED_TERMS_WITH_SPACES[feed]

    feed_in_db = database_feed_prefix + feed

    # Special case: if there are no terms specified, then it's automatically added to this feed
    # Todo: this may want to be coded more neatly
    if terms is None:
        labels[feed_in_db] = True
        return

    # Otherwise, we check against all feeds
    # Firstly, check emoji
    labels[feed_in_db] = _emoji_in_post(terms, post)

    # Then check words if the emoji wasn't already a hit
    if not labels[feed_in_db]:
        labels[feed_in_db] = _word_in_post(terms, words)

    # Special case: add all posts in other feeds to the Astronomy feed
    # Todo: this may want to be coded more neatly, its an absolute mess!!!
    if labels[feed_in_db] and feed != "astro" and feed != "questions" and feed != "all":
        labels[database_feed_prefix + "astro"] = True

        # Special case: add all posts in science feeds to the research feed
        if feed != "research" and feed != "astrophotos":
            labels[database_feed_prefix + "research"] = True


def _emoji_in_post(terms, post):
    return any([emoji in post for emoji in terms["emoji"]])


def _word_in_post(terms, words):
    return any([word in terms["words"] for word in words])


def post_in_feeds(
    post: str, feeds: None | Iterable[str] = None, database_feed_prefix: str = "feed_"
) -> dict:
    """Tests if a given post is in the defined feeds by checking its text; returns none if so."""
    words = cleaned_word_list(post)
    labels = {}

    if feeds is None:
        feeds = FEED_TERMS_WITH_SPACES.keys()

    for feed in feeds:
        label_post(
            labels,
            post,
            words,
            feed,
            database_feed_prefix=database_feed_prefix,
        )

    return labels
