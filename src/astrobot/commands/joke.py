"""Tells a joke."""

from __future__ import annotations

from astrobot.database import new_bot_action
from ._base import Command
from atproto_client.models.app.bsky.notification.list_notifications import Notification
from random import randint
from ..post import send_post
from atproto import Client, models


# i am so sorry
jokes = [
    "What kind of songs do the planets like to sing? Nep-tunes!",
    "What does an astronomer blow with gum? Hubbles!",
    "A neutrino walks into a bar... and keeps right on going.\n\nSeriously, where did you think this joke was going?",
    "Orion's Belt is a big waist of space.\n\nSorry, very average pun - only three stars.",
    "I tried looking at the solar eclipse using a colander, but I ended up straining my eyes...",
    "Why didn't the Dog Star laugh at the joke?\n\nA: It was too Sirius",
    "How does the astronaut on the moon cut his hair?\n\nA: Eclipse it…",
    "My favourite name for a planet is Saturn. It has a nice ring to it.",
    "Have you heard about the new restaurant on the moon?\n\nThe food is good, but there's just no atmosphere.",
    "Why didn't the sun go to college?\n\nA: Because it already had six million degrees!",
    "Why haven't aliens visited our solar system?\n\nA: They looked at the reviews and we only have one star.",
    "What's the worst thing about throwing a party in space?\n\nA: You have to planet.",
    "What is an astronaut's favorite key on a keyboard?\n\nA: The space bar.",
    "The rotation of the Earth makes my day!",
    "Why does the moon orbit the Earth?\n\nA: To get to the other side!",
    "How do astronomers see in the dark?\n\nA: They use standard candles!",
    "Why wasn't the disturbed spiral galaxy let into the nightclub?\n\nA: He had previously been barred.",
    "How many astronomers does it take to change a light bulb?\n\nA: Just one! They've got all night because it's cloudy.",
]


JOKE_INDEX = randint(0, len(jokes) - 1)


class JokeCommand(Command):
    command = "joke"

    def __init__(self, notification: Notification):
        self.notification = notification

    @staticmethod
    def is_instance_of(
        words: list[str], notification: Notification
    ) -> None | JokeCommand:
        if words[0] == JokeCommand.command:
            return JokeCommand(notification)

    def execute(self, client: Client):
        global JOKE_INDEX
        post_ref = models.create_strong_ref(self.notification)
        send_post(client, jokes[JOKE_INDEX], root_post=post_ref)

        new_bot_action(
            did=self.notification.author.did,
            type=self.command,
            stage="completed",
            parent_uri=post_ref.uri,
            parent_cid=post_ref.cid,
            latest_uri=post_ref.uri,
            latest_cid=post_ref.cid,
            completed=True,
        )

        # todo improve this unsanctimonious use of a (*gasps*) global variable!!!
        JOKE_INDEX = (JOKE_INDEX + 1) % len(jokes)
