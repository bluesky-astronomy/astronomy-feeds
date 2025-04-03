"""Infrastructure for created bluesky notification objects

todo:
    * replace oject type hints with actual specific subclasses
"""

from atproto import models

supported_notification_types = ["mention", "reply", "like"]


#
# "construct" functions, which are just wrappers around various atproto constructors
#
def construct_facet_mention(
    did: str = "mention author did", py_type: str = "app.bsky.richtext.facet#mention"
) -> models.app.bsky.richtext.facet.Mention:
    """wraps models.app.bsky.richtext.facet.Mention constructor"""
    return models.app.bsky.richtext.facet.Mention(did=did, py_type=py_type)


def construct_facet_byteslice(
    byte_end: int = 41,
    byte_start: int = 13,
    py_type: str = "app.bsky.richtext.facet#byteSlice",
) -> models.app.bsky.richtext.facet.ByteSlice:
    """wraps models.app.bsky.richtext.facet.ByteSlice constructor"""
    return models.app.bsky.richtext.facet.ByteSlice(
        byte_end=byte_end, byte_start=byte_start, py_type=py_type
    )


def construct_facet_main(
    features: list = [], index: object = None, py_type: str = "app.bsky.richtext.facet"
) -> models.app.bsky.richtext.facet.Main:
    """wraps models.app.bsky.richtext.facet.Main constructor"""
    return models.app.bsky.richtext.facet.Main(
        features=features, index=index, py_type=py_type
    )


def construct_strong_ref_main(
    cid: str = "ref cid",
    uri: str = "ref uri",
    py_type: str = "com.atproto.repo.strongRef",
) -> models.com.atproto.repo.strong_ref.Main:
    """wraps models.com.atproto.repo.strong_ref.Main constructor"""
    return models.com.atproto.repo.strong_ref.Main(cid=cid, uri=uri, py_type=py_type)


def construct_post_record(
    created_at: str = "created-at datetime",
    text: str = "post text",
    embed: object = None,
    entities: object = None,
    facets: list = [],
    labels: object = None,
    langs: list[str] = ["en"],
    reply: object = None,
    tags: object = None,
    py_type: str = "app.bsky.feed.post",
) -> models.app.bsky.feed.post.Record:
    """wraps models.app.bsky.feed.post.Record constructor"""
    return models.app.bsky.feed.post.Record(
        created_at=created_at,
        text=text,
        embed=embed,
        entities=entities,
        facets=facets,
        labels=labels,
        langs=langs,
        reply=reply,
        tags=tags,
        py_type=py_type,
    )


def construct_like_record(
    created_at: str = "datetime record created at",
    subject: object = None,
    py_type: str = "app.bsky.feed.like",
) -> models.app.bsky.feed.like.Record:
    """wraps models.app.bsky.feed.like.Record constructor"""
    return models.app.bsky.feed.like.Record(
        created_at=created_at, subject=subject, py_type=py_type
    )


#
# "build" functions put specific kinds of objects together, with logic and/or field value choices
# particular to those objects
#
def build_reply_ref(
    parent_ref_cid: str = "replied-to post cid",
    parent_ref_uri: str = "replied-to post uri",
    root_ref_cid: str = "replied-to post's root post cid",
    root_ref_uri: str = "replied-to post's root post uri",
    py_type: str = "app.bsky.feed.post#replyRef",
) -> models.app.bsky.feed.post.ReplyRef:
    """builds a models.app.bsky.feed.post.ReplyRef object"""
    # configure two strong references appropriately
    parent_ref = construct_strong_ref_main(cid=parent_ref_cid, uri=parent_ref_uri)
    root_ref = construct_strong_ref_main(cid=root_ref_cid, uri=root_ref_uri)

    reply_ref = models.app.bsky.feed.post.ReplyRef(
        parent=parent_ref, root=root_ref, py_type=py_type
    )

    return reply_ref


def build_profileview(
    did: str = "profile did",
    handle: str = "profile handle",
    associated: object = None,
    avatar: str = "profile image link",
    created_at: str = "datetime profile created at",
    description: str = "profile description",
    display_name: str = "profile display name",
    indexed_at: str = "datetime profile indexed at",
    labels: list = [],
    viewer: object = None,
    py_type: str = "app.bsky.actor.defs#profileView",
) -> models.app.bsky.actor.defs.ProfileView:
    """builds a models.app.bsky.actor.defs.ProfileView object"""
    # for now I don't think any of the ViewerState values will matter, so I'll just define it like this
    if viewer is None:
        viewer = models.app.bsky.actor.defs.ViewerState(
            blocked_by=False,
            blocking=None,
            blocking_by_list=None,
            followed_by=None,
            following=None,
            known_followers=None,
            muted=False,
            muted_by_list=None,
            py_type="app.bsky.actor.defs#viewerState",
        )

    author = models.app.bsky.actor.defs.ProfileView(
        did=did,
        handle=handle,
        associated=associated,
        avatar=avatar,
        created_at=created_at,
        description=description,
        display_name=display_name,
        indexed_at=indexed_at,
        labels=labels,
        viewer=viewer,
        py_type=py_type,
    )

    return author


def build_notification(
    notification_type: str,
    author: object = None,
    cid: str = "notifying post cid",
    indexed_at: str = "datetime indexed at",
    is_read: bool = False,
    reason: str = "reason for notification",
    record: object = None,
    uri: str = "template uri",
    labels: list = [],
    reason_subject: str = None,
    py_type="app.bsky.notification.listNotifications#notification",
    # important quantities to have easy control of on user end
    record_text: str = None,
    author_did: str = None,
) -> models.app.bsky.notification.list_notifications.Notification:
    """builds a notification object

    Default values are given for all arguments, and will be modified as needed based on the notification type.

    Currently, easy access via argument values is provided only to a subset of fields that are deemed useful
    to be able to set the values of at call time; this list may expand as needed.
    """
    # make sure we can do the type of notification requested
    if notification_type not in supported_notification_types:
        raise ValueError(
            f"build_notification: passed unsupported type={notification_type}; can only generate notifications of types in {supported_notification_types}"
        )

    # modify default values as needed per type
    match notification_type:
        case "mention":
            if author is None:
                author = build_profileview(
                    did=(
                        author_did
                        if author_did is not None
                        else "mentioning account did"
                    ),
                    handle="mentioning account profile handle",
                    avatar="link to mentioning account profile image",
                    description="mentioning account profile description",
                    display_name="mentioning account profile display name",
                )

            cid = "mentioning post cid"

            reason = "mention"

            if record is None:
                facet_feature = construct_facet_mention(did="mentioned account did")
                facets = [
                    construct_facet_main(
                        features=[facet_feature], index=construct_facet_byteslice()
                    )
                ]
                record = construct_post_record(
                    text=(
                        record_text
                        if record_text is not None
                        else "mentioning post text"
                    ),
                    facets=facets,
                )

            uri = "mentioning post uri"

            reason_subject = None

        case "reply":
            if author is None:
                author = build_profileview(
                    did=(
                        author_did if author_did is not None else "replying account did"
                    ),
                    handle="replying account profile handle",
                    avatar="link to replying account profile image",
                    description="replying account profile description",
                    display_name="replying account profile display name",
                )

            cid = "replying post cid"

            reason = "reply"

            if record is None:
                reply = build_reply_ref(
                    parent_ref_cid="replied-to post cid",
                    parent_ref_uri="replied-to post uri",
                    root_ref_cid="replied-to post's root post cid",
                    root_ref_uri="replied-to post's root post uri",
                )
                record = construct_post_record(
                    text=(
                        record_text
                        if record_text is not None
                        else "mentioning post text"
                    ),
                    reply=reply,
                )

            uri = "replying post uri"

            reason_subject = record.reply.parent.uri

        case "like":
            if author is None:
                author = build_profileview(
                    did=(
                        author_did if author_did is not None else "liking account did"
                    ),
                    handle="liking account profile handle",
                    avatar="link to liking account profile image",
                    description="liking account profile description",
                    display_name="liking account profile display name",
                )

            cid = "like cid"

            reason = "like"

            if record is None:
                subject = construct_strong_ref_main(
                    cid="liked post cid", uri="liked post uri"
                )
                record = construct_like_record(subject=subject)

            uri = "like uri"

            reason_subject = record.subject.uri

        case _:
            # default, should not reach here
            raise ValueError(
                f"build_notification: passed type={notification_type}, cannot handle."
            )

    # build the notification
    notification = models.app.bsky.notification.list_notifications.Notification(
        author=author,
        cid=cid,
        indexed_at=indexed_at,
        is_read=is_read,
        reason=reason,
        record=record,
        uri=uri,
        labels=labels,
        reason_subject=reason_subject,
        py_type=py_type,
    )

    return notification
