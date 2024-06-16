"""Base class for commands."""
from abc import ABC, abstractmethod
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from __future__ import annotations


class AbstractCommand(ABC):

    @staticmethod
    @abstractmethod
    def is_instance_of(command: str) -> None | AbstractCommand:
        """Check if a given string is a valid example of this command.
        
        If yes, then return an intialized version of this class with the command 
        assigned.

        If no, return None.
        """
        pass
    
    @abstractmethod
    def execute(self):
        """Executes the next step of a given command, or update to a command."""
        pass

    @abstractmethod
    def 


    

