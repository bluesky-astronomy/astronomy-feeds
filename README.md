# Astronomy feeds on Bluesky

A multiprocess Python module for ingesting operations from the [Bluesky](https://bsky.app) firehose. Powered by [the AT Protocol SDK](https://atproto.blue).

This module was originally based on MarshalX's [bluesky-feed-generator](https://github.com/MarshalX/bluesky-feed-generator), but includes some extra optimizations (although its main bottleneck is still Python multiprocessing overhead.)

## About the Astronomy feeds

The [Astronomy feeds](https://bsky.app/profile/emily.space/feed/astro) on [Bluesky](https://bsky.app/) are a set of 'custom algorithms' that collate astronomy content on Bluesky. This repository is one component of a multiple-service system to host the feeds.

## Installing the service

Create a fresh virtual environment with the Python version defined in runtime.txt. Then, install with `pip install -e .`.

Using uv? Then installing is as easy as running `uv sync`.

This module uses [faster-fifo](https://github.com/alex-petrenko/faster-fifo) for fast communication between processes; you may need to install some basic compile tools to get it to work, if you don't already have them (`sudo apt install --reinstall build-essential gcc g++`).

## Running the app

You can start the app with the 'run' script, or the command

```
python -m astrofeed_firehose
```

If you're using uv, that's

```
uv run python -m astrofeed_firehose
```
