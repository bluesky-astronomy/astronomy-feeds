"""Test of how to fetch details of content that's gone stale."""

from astrofeed_lib.database import db, BotActions
from datetime import datetime, timedelta
from astrobot.client import get_client
from atproto import models
from astrobot.notifications import LikeNotification, ReplyNotification


actions_of_interest = (
    BotActions.select()
    .where(
        BotActions.type == "signup",
        BotActions.complete == False,  # noqa: E712
        BotActions.indexed_at > datetime.now() - timedelta(days=7),
    )
    .limit(25)
)

uris_of_interest = [x.latest_uri for x in actions_of_interest]

client = get_client()
# posts = client.get_posts(uris_of_interest).posts

posts = client.get_posts(
    ["at://did:plc:fe7v6gvpput3klm5wbjqotbi/app.bsky.feed.post/3lb7wyj7nz22i"]
).posts

posts = [post for post in posts if post.like_count > 0 or post.reply_count > 0]


def basic_profile_view_to_profile_view(
    profile: models.AppBskyActorDefs.ProfileViewBasic,
) -> models.AppBskyActorDefs.ProfileView:
    """Converts a ProfileViewBasic (which misses 'description' and 'indexed_at') to a
    semi-complete ProfileView, missing those fields but with correct type.
    """
    return models.AppBskyActorDefs.ProfileView(
        associated=profile.associated,
        avatar=profile.avatar,
        created_at=profile.created_at,
        did=profile.did,
        display_name=profile.display_name,
        handle=profile.handle,
        labels=profile.labels,
        viewer=profile.viewer,
    )


def reply_to_reply_notification(reply):
    return models.AppBskyNotificationListNotifications.Notification(
        author=basic_profile_view_to_profile_view(reply.post.author),
        cid=reply.post.cid,
        indexed_at=reply.post.indexed_at,
        is_read=False,
        reason="reply",
        record=reply.post.record,
        uri=reply.post.uri,
    )


def like_to_like_notification(like, post):
    return models.AppBskyNotificationListNotifications.Notification(
        author=like.actor,
        indexed_at=like.indexed_at,
        is_read=False,
        reason="like",
        record=models.AppBskyFeedLike.Record(
            created_at=like.created_at,
            subject=models.create_strong_ref(post)
        ),
        # CID and URI of the like record itself is unknown!
        cid="unknown",
        uri="unknown"
    )


notifications = []
for post in posts:
    print(f"POST: {post.record.text}")
    if post.reply_count > 0:
        print("... WITH REPLIES:")
        replies = client.get_post_thread(post.uri, depth=1).thread
        if isinstance(replies, models.AppBskyFeedDefs.ThreadViewPost):
            for reply in replies.replies:
                if isinstance(reply, models.AppBskyFeedDefs.ThreadViewPost):
                    notifications.append(reply_to_reply_notification(reply))

    if post.like_count > 0:
        print("... WITH LIKES:")
        # Bluesky has a max of 100. We probably never need more than this anyway here.
        likes = client.get_likes(post.uri, limit=100)
        print(likes.likes)
        for like in likes.likes:
            notifications.append(like_to_like_notification(like, post))


# Sort by bluesky index time (ascending)
notifications.sort(key=lambda x: x.indexed_at)


for notification in notifications:
    print("NOTIFICATION: ------------------------------")
    print(notification.indexed_at, notification.reason)

    if notification.reason == "like":
        final_not = LikeNotification(notification)
        final_not.fetch_root_ref(client)

    elif notification.reason == "reply":
        final_not = ReplyNotification(notification)
