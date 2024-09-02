"""Extremely barebones firehose client for testing the absolute top speed of commit
downloading from Bluesky. See also the async version (a bit faster.)
https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos.py
"""

from atproto import FirehoseSubscribeReposClient, firehose_models, parse_subscribe_repos_message

client = FirehoseSubscribeReposClient()


def on_message_handler(message: firehose_models.MessageFrame) -> None:
    print(message.header, parse_subscribe_repos_message(message))


client.start(on_message_handler)
