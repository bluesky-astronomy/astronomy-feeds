"""Set of functions specifying everything about all feeds."""
import re
import peewee
from .config import FEED_TERMS


def remove_links_from_post(post: str) -> str:
    """Remove all links from the text of a post.
    Modified from https://stackoverflow.com/questions/11331982/how-to-remove-any-url-within-a-string-in-python
    """
    return re.sub(r"https?:\/{2}\S+", "", post)


# The same as string.punctuation in the base library, except we want to keep hashtags and also add newline etc chars
# to the list of punctuation identifiers to remove
PUNCTUATION = list("""!"$%&'()*+,-./:;<=>?@[\]^_`{|}~""") + ["\n", "\r"]


def remove_punctuation_from_post(post: str) -> str:
    """Removes all punctuation from a post - EXCEPT hashtags!"""
    return "".join([x if x not in PUNCTUATION else " " for x in post.lower()])


def cleaned_word_list(post: str) -> list:
    """Generates a list of all words in a post. 
    
    Words include a space at the start AND end, like:
    ' #astro '
    ' space '
    meaning that matches against these strings must be to whole terms.
    """
    post = remove_links_from_post(post)
    post = remove_punctuation_from_post(post)
    return [f" {word} " for word in post.split()]


FEED_TERMS_WITH_SPACES = dict()
for feed, terms in FEED_TERMS.items():
    FEED_TERMS_WITH_SPACES[feed] = [f" {term} " for term in terms]


def post_in_feeds(post: str) -> dict:
    """Tests if a given post is in the defined feeds by checking its text; returns none if so."""
    words = cleaned_word_list(post)
    labels = {}

    # Todo refactor this to remove nesting + make more developable (thats a word, dont @ me)
    for feed, terms in FEED_TERMS_WITH_SPACES.items():
        # All posts without a given term are added to this feed
        if terms is None:
            labels[feed] = True

        # Otherwise, we check against all feeds
        else:
            labels[feed] = any([True for word in words if word in terms])

            # Add all posts in other feeds to the Astronomy feed
            if feed != "astro" and labels[feed]:
                labels["astro"] = True

    return labels
    