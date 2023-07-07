import logging

from atproto import models

from server.database import db, Post, Account

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def operations_callback(ops: dict) -> None:
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync

    # for example, let's create our custom feed that will contain all posts that contains alf related text

    posts_to_create = []
    valid_dids = {account.did for account in Account.select()}
    valid_posts = [post for post in ops['posts']['created'] if post['author'] in valid_dids]

    for created_post in valid_posts:
        post_dict = {
            'uri': created_post['uri'],
            'cid': created_post['cid'],
            'author': created_post['author'],
            'feed_all': True,
            # 'reply_parent': reply_parent,
            # 'reply_root': reply_root,
        }
        posts_to_create.append(post_dict)

    posts_to_delete = [p['uri'] for p in ops['posts']['deleted']]
    if posts_to_delete:
        Post.delete().where(Post.uri.in_(posts_to_delete))
        logger.info(f'Deleted from feed: {len(posts_to_delete)}')

    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added to feed: {len(posts_to_create)}')
