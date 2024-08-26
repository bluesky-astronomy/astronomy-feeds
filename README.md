# Astronomy feeds on Bluesky

Python module powered by [The AT Protocol SDK for Python](https://atproto.blue) for crawling the [Bluesky](https://bsky.app) firehose of posts and finding all that match criteria specified by the Astronomy feeds.

This module was originally based on MarshalX's [bluesky-feed-generator](https://github.com/MarshalX/bluesky-feed-generator), but differs in its approach to multiprocessing (which is AWS-compatible) and in how it implements watchdog functionality to detect crashed subprocesses.

## About the Astronomy feeds

The [Astronomy feeds](https://bsky.app/profile/emily.space/feed/astro) on [Bluesky](https://bsky.app/) are a set of 'custom algorithms' that collate astronomy content on Bluesky. This repository is one component of a multiple-service system to host the feeds.

## Installing the service

Create a fresh virtual environment with the Python version defined in runtime.txt. Then, install with `pip install -e .`.

## Running the app

You can start the webapp with the 'run' script, or the command

```
python -m astrofeed_firehose
```
