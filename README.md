# Astronomy feeds on Bluesky

A multiprocess Python module for ingesting operations from the [Bluesky](https://bsky.app) firehose. Powered by [the AT Protocol SDK](https://atproto.blue).

This module was originally based on MarshalX's [bluesky-feed-generator](https://github.com/MarshalX/bluesky-feed-generator), but includes some extra optimizations (although its main bottleneck is still Python multiprocessing overhead.)

## About the Astronomy feeds

The [Astronomy feeds](https://bsky.app/profile/emily.space/feed/astro) on [Bluesky](https://bsky.app/) are a set of 'custom algorithms' that collate astronomy content on Bluesky. This repository is one component of a multiple-service system to host the feeds.


## Developing

### Installing

1. Download the module with

```bash
git clone https://github.com/bluesky-astronomy/astronomy-feeds.git
```

2. Ensure that you have uv installed to manage Python (see the [development guide](https://github.com/bluesky-astronomy/development-guide))

3. This module assumes you have basic compile tools installed, and this module may not work on operating systems other than Linux. That's because this module uses [faster-fifo](https://github.com/alex-petrenko/faster-fifo) for fast communication between processes; you may additionally need to do `sudo apt install --reinstall build-essential gcc g++`.

4. Set up the environment variables (see below).

5. Start the service with:

```bash
uv run -m astrofeed_firehose
```

### Environment variables

To run the service, you'll need to set the following environment variables.

**Mandatory:**

- `BLUESKY_DATABASE` - either a path to an SQLite development database (if `ASTROFEED_PRODUCTION` is false), or a connection string for a remote MySQL database (if `ASTROFEED_PRODUCTION` is true.) The MySQL database connection string should have the format `mysql://USER:PASSWORD@HOST:PORT/NAME?ssl-mode=REQUIRED`.

**Mandatory in production:**

- `ASTROFEED_PRODUCTION` - set to True to instead connect to a remote MySQL database

**Optional settings:**

- `FIREHOSE_WORKER_COUNT` - number of post-processing workers. Defaults to your number of CPU cores; in general, setting this higher than ~2-4 isn't necessary, although it depends a lot on the speed of the post-processing workers on your machine.
- `FIREHOSE_BASE_URI` - websocket to fetch posts from. Defaults to `wss://bsky.network/xrpc`.
- `FIREHOSE_CURSOR_OVERRIDE` - cursor override to use when starting the firehose. Defaults to None, and it will instead fetch a cursor from the database. If the database cursor does not exist or is too old, the firehose will instead use the cursor of the latest Bluesky firehose commit.

## Running the service

You can then start the service with the command

```
uv run python -m astrofeed_firehose
```
