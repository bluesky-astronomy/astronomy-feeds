from string import punctuation
from .data import astronomy_terms
from server import config
from server.database import Post
from ._algorithm import Algorithm, account_function_only_valid


PUNCTUATION_MAPPING = {k: " " for k in list(punctuation) + ["\n", "\r"]}


print("test galaxy string! hi hello.".translate(PUNCTUATION_MAPPING).split())

def post_is_valid(post: str) -> bool:
    """Checks if a given post is a valid example of a post for the astro feed."""
    if "🔭" in post:
        return True
    
    # Remove all punctuation from the post
    words = [f" {x} " for x in post.translate(PUNCTUATION_MAPPING).split()]

    print(words)

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


algorithm = Algorithm(config.URI_ASTRO, account_selection_function=account_function_only_valid)


# def handler(cursor: Optional[str], limit: int) -> dict:

#     valid_dids = Account.select(Account.did).where(Account.is_valid)

#     posts = (Post
#         .select()
#         .where(Post.author.in_(valid_dids))
#         .order_by(Post.indexed_at.desc())
#         # .order_by(Post.cid.asc())
#         .limit(limit)
#     )

#     if cursor:
#         cursor_parts = cursor.split('::')
#         if len(cursor_parts) != 2:
#             raise ValueError('Malformed cursor')

#         indexed_at, cid = cursor_parts
#         indexed_at = datetime.fromtimestamp(int(indexed_at) / 1000)
#         posts = posts.where(Post.indexed_at <= indexed_at).where(Post.cid < cid)

#     feed = [{'post': post.uri} for post in posts]

#     cursor = None
#     last_post = posts[-1] if posts else None
#     if last_post:
#         cursor = f'{int(last_post.indexed_at.timestamp() * 1000)}::{last_post.cid}'

#     return {
#         'cursor': cursor,
#         'feed': feed
#     }
