"""Standard functions for posting posts and threads on Bluesky."""

from atproto import Client, models, client_utils
import warnings

MAX_POST_LENGTH = 300


def check_post_text(text):
    """Checks post text for Bluesky spec compliance"""
    # Todo is this function super necessary? I think the checking in atproto is already very good!
    # Assume that it's fine if it's a TextBuilder
    if isinstance(text, client_utils.TextBuilder):
        return
    if not isinstance(text, str):
        raise ValueError("post text must be a string!")
    if len(text) == 0:
        raise ValueError("no post text specified ('text' is an empty string)")
    if len(text) > MAX_POST_LENGTH:
        raise ValueError(
            f"post too long! Must be shorter than {MAX_POST_LENGTH} characters."
        )


def check_post_image(image, image_alt):
    """Check that there's valid image and valid alt text if an image is specified"""
    if image is None:
        return
    # Todo: probably not needed; 
    # if not isinstance(image, bytes):
    #     raise ValueError("image must be a bytes representation of the image's data!")
    if not isinstance(image_alt, str):
        warnings.warn(UserWarning("An image post is missing alt text."))


def check_post_reply_info(root_post, parent_post):
    """Checks that the reply info of a post is compliant with required spec."""
    # If no reply specified
    if root_post is None:
        if parent_post is not None:
            raise ValueError(
                "post reply incorrectly specified! Parent post of thread was given but no thread root."
            )
        return root_post, parent_post

    # If at least root_post specified
    if not isinstance(root_post, models.ComAtprotoRepoStrongRef.Main):
        raise ValueError(
            "root post must be a models.ComAtprotoRepoStrongRef.Main instance!"
        )
    if parent_post is None:
        parent_post = root_post
        return root_post, parent_post

    # If parent_post specified too
    if not isinstance(parent_post, models.ComAtprotoRepoStrongRef.Main):
        raise ValueError(
            "root post must be a models.ComAtprotoRepoStrongRef.Main instance!"
        )
    return root_post, parent_post


def get_reply_info(root_post, parent_post):
    """Checks reply info (root post and parent post) before returning a post reply model if relevant."""
    root_post, parent_post = check_post_reply_info(root_post, parent_post)
    if root_post is None:
        return None
    return models.AppBskyFeedPost.ReplyRef(parent=parent_post, root=root_post)


def get_embed_info(embed, quote):
    # Quote post gets priority
    if isinstance(quote, models.ComAtprotoRepoStrongRef.Main):
        return models.AppBskyEmbedRecord.Main(record=quote)
    if isinstance(embed, models.AppBskyEmbedExternal.External):
        return models.AppBskyEmbedExternal.Main(external=embed)
    return None


def send_post(
    client: Client,
    text: str | client_utils.TextBuilder,
    image: str | None = None,
    image_alt: str | None = None,
    root_post: models.ComAtprotoRepoStrongRef.Main | None = None,
    parent_post: models.ComAtprotoRepoStrongRef.Main | None = None,
    embed: models.AppBskyEmbedExternal.External | None = None,
    quote: models.ComAtprotoRepoStrongRef.Main | None = None,
):
    """Uploads a post (including an image, if desired!) to the Bluesky network."""
    check_post_text(text)
    check_post_image(image, image_alt)
    reply_info = get_reply_info(root_post, parent_post)

    # Send an image, if desired
    if image:
        response = client.send_image(
            text=text, image=image, image_alt=image_alt, reply_to=reply_info
        )
    else:
        embed_info = get_embed_info(embed, quote)
        response = client.send_post(text=text, reply_to=reply_info, embed=embed_info)

    this_post = models.create_strong_ref(response)
    if root_post is None:
        root_post = this_post

    return root_post, this_post


def convert_string_into_thread(
    long_string: str, separator: str = ">", with_thread_numbers: bool = True
) -> list:
    """Turns a long string into a thread of posts, preferentially splitting at punctuation marks."""
    pass


def send_thread(
    client: Client,
    posts: list[str]
    | list[client_utils.TextBuilder]
    | list[str | client_utils.TextBuilder],
    images: dict[int, str] | None = None,
    image_alts: dict[int, str] | None = None,
    root_post: models.ComAtprotoRepoStrongRef.Main | None = None,
    parent_post: models.ComAtprotoRepoStrongRef.Main | None = None,
    embeds: dict[int, str] | None = None,
    quotes: dict[int, str] | None = None,
):
    """Sends a thread of posts, automatically splitting up long text into a thread!
    # Todo: consider type checking as Sequence, not list (not sure how)
    """
    # Initialise some things so that they're dicts and have a .has method
    if images is None:
        images = dict()
    if image_alts is None:
        image_alts = dict()
    if embeds is None:
        embeds = dict()
    if quotes is None:
        quotes = dict()

    # Todo: allow posts to be just a string that we split automatically
    # Todo: check that all iterables have same length, if lists specified
    # Todo: check that images iterable matches image_alts iterable. Consider making it just one parameter instead?
    for post_number, a_post in enumerate(posts):
        root_post, parent_post = send_post(
            client,
            a_post,
            image=images.get(post_number),
            image_alt=image_alts.get(post_number),
            root_post=root_post,
            parent_post=parent_post,
            embed=embeds.get(post_number),
            quote=quotes.get(post_number),
        )

    return root_post, parent_post


def get_post(client: Client, reference):
    """Fetch a post on the Bluesky network based on its uri and cid. Differs from the
    native atproto implementation which makes this a little harder.

    Reference must have fields 'uri' and 'cid'.
    """
    # bit sketch but it works, don't @ me
    repo, collection, record_key = reference.uri.replace("at://", "").split("/")

    return client.get_post(record_key, repo, reference.cid)
