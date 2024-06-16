"""Initial entrypoints for processing commands to the bot."""
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from ..moderation import get_moderators


def process_commands(notifications: list[Notification]):
    print("Processing notifications...")

    moderators = get_moderators()

    # Sort all types of notification into groups
    likes = []
    mentions = []
    replies = []

    for notification in notifications:
        match notification.reason:
            case "like":
                likes.append(notification)
            case "mention":
                mentions.append(notification)
            case "reply":
                replies.append(notification)

    # Process all types of notification
    _process_mentions(mentions, moderators)
    _process_replies(replies, moderators)
    _process_likes(likes, moderators)



def _process_mentions(notifications: list[Notification], moderators: list[str]):
    """Process mentions to the bot.
    
    This includes all checking of commands, adding them to the bot's queue.
    """
    # Cycle over each command and try to find its type
    # for notification in notifications:
    #     match notification.reason:
    #         case "like":
    #             likes.append(notification)
    #         case "mention":
    #             mentions.append(notification)
    #         case "reply":
    #             replies.append(notification)
    # todo
    pass


def _process_replies(notifications: list[Notification], moderators: list[str]):
    """Process replies to the bot's own posts.
    
    This allows for advanced functionality, including 
    """
    # todo
    pass


def _process_likes(notifications: list[Notification], moderators: list[str]):
    """Processes likes on posts.
    
    Currently, the only reason to do this is to get moderator approval on signups.
    """
    # todo
    pass
