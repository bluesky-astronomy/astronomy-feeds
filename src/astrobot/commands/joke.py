"""Tells a joke."""
from ._base import AbstractCommand
from __future__ import annotations
from atproto_client.models.app.bsky.notification.list_notifications import Notification


class Joke(AbstractCommand):
    def __init__(self, notification: Notification):
        self.notification = notification

    @staticmethod
    def is_instance_of(command: str, notification: Notification) -> None | Joke:
        if command == Joke:
            return Joke(notification)
        
    def execute(self):
        # todo
        pass