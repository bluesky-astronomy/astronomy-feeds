"""Standard functions for posting posts and threads on Bluesky."""

from atproto import Client, models, client_utils


MAX_POST_LENGTH = 300


def check_post_text(text):
    """Checks post text for Bluesky spec compliance"""
    # todo does not support TextMaker
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
    if not isinstance(image, str):
        raise ValueError("image must be a string representation of the image's data!")
    if not isinstance(image_alt, str):
        raise ValueError("You must specify alt text when uploading an image!")


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
    return models.AppBskyFeedPost.ReplyRef(parent=parent_post, root=parent_post)


def send_post(
    client: Client,
    text: str | client_utils.TextBuilder,
    image: str | None = None,
    image_alt: str | None = None,
    root_post: models.ComAtprotoRepoStrongRef.Main | None = None,
    parent_post: models.ComAtprotoRepoStrongRef.Main | None = None,
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
        response = client.send_post(text=text, reply_to=reply_info)

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
    images: dict[int, str] = None,
    image_alts: dict[int, str] = None,
    root_post: models.ComAtprotoRepoStrongRef.Main | None = None,
    parent_post: models.ComAtprotoRepoStrongRef.Main | None = None,
):
    """Sends a thread of posts, automatically splitting up long text into a thread!
    # Todo: consider type checking as Sequence, not list (not sure how)
    """
    # Todo: allow posts to be just a string that we split automatically
    # Todo: check that all iterables have same length, if lists specified
    # Todo: if dicts specified, check that there are enough posts for all of them
    # Todo: check that images iterable matches image_alts iterable. Consider making it just one parameter instead?
    for post_number, a_post in enumerate(posts):
        root_post, parent_post = send_post(
            client,
            a_post,
            image=images.get(post_number),
            image_alts=image_alts.get(post_number),
            root_post=root_post,
            parent_post=parent_post,
        )

    return root_post, parent_post
