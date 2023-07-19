from .data import astronomy_terms
from server import config
from server.database import Post
from ._algorithm import Algorithm
from string import punctuation

# The same as string.punctuation in the base library, except we want to keep hashtags and also add newline etc chars
# to the list of punctuation identifiers to remove
PUNCTUATION = list("""!"$%&'()*+,-./:;<=>?@[\]^_`{|}~""") + ["\n", "\r"]


def post_is_valid(post: str) -> bool:
    """Checks if a given post is a valid example of a post for the astro feed."""
    if "🔭" in post:
        return True
    
    # Remove all punctuation from the post
    post_cleaned = "".join([x if x not in PUNCTUATION else " " for x in post.lower()])
    words = [f" {x} " for x in post_cleaned.split()]

    # See if any of the words are in our list of valid astronomy terms
    return any([True for x in words if x in astronomy_terms])


class AstroAlgorithm(Algorithm):
    def __init__(self, uri, account_selection_function=None) -> None:
        super().__init__(uri, account_selection_function)

    def select_posts(self, valid_dids, limit):
        """Selects only posts that are tagged as being valid"""
        return (Post
            .select()
            .where(Post.author.in_(valid_dids), Post.feed_astro == True)
            .order_by(Post.indexed_at.desc())
            .limit(limit)
        )


algorithm = AstroAlgorithm(config.URI_ASTRO)
