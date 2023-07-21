import logging
from server.database import db, Post
from .accounts import AccountList
from .algos.astro import post_is_valid


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
    

account_list = AccountList()


def operations_callback(ops: dict) -> None:
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync

    # for example, let's create our custom feed that will contain all posts that contains alf related text

    posts_to_create = []
    valid_dids = account_list.get_accounts()
    valid_posts = [post for post in ops['posts']['created'] if post['author'] in valid_dids]

    astro_feed_counter = 0
    for created_post in valid_posts:
        post_text = created_post['record']['text']
        add_to_feed_astro = post_is_valid(post_text)
        astro_feed_counter += int(add_to_feed_astro)

        post_dict = {
            'uri': created_post['uri'],
            'cid': created_post['cid'],
            'author': created_post['author'],
            'text': post_text,
            'feed_all': True,
            'feed_astro': add_to_feed_astro,
            # 'reply_parent': reply_parent,
            # 'reply_root': reply_root,
        }
        posts_to_create.append(post_dict)

    posts_to_delete = [post['uri'] for post in ops['posts']['deleted']]
    if posts_to_delete:
        if db.is_closed():
            db.connect()
        Post.delete().where(Post.uri.in_(posts_to_delete))
        # logger.info(f'Deleted from feed: {len(posts_to_delete)}')

    if posts_to_create:
        if db.is_closed():
            db.connect()
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added to astro-all: {len(posts_to_create)}; astro: {astro_feed_counter}')
