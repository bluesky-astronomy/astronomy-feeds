"""Extremely barebones firehose client for testing the absolute top speed of commit
downloading from Bluesky. Forked from 
https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos_async.py
"""

import uvloop
import time

from atproto import (
    AsyncFirehoseSubscribeReposClient,
    firehose_models,
    models
)


start_time = time.time()
n_commits = 0


async def on_message_handler(message: firehose_models.MessageFrame) -> None:
        # print(message.header, parse_subscribe_repos_message(message))
        global n_commits, start_time
        n_commits = n_commits + 1
        if n_commits % 10000 == 0:
            print(f"{10000 / (time.time() - start_time):.2f} ops/second")
            start_time = time.time()
        return


async def main() -> None:
    params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=0)
    client = AsyncFirehoseSubscribeReposClient(params=params)
    await client.start(on_message_handler)


if __name__ == '__main__':
    # use run() for a higher Python version
    uvloop.run(main())
