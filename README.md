# astrobot

A bot that handles actions on the Astronomy feeds, like signups. It will also eventually include moderation and DM tools. 

## About the Astronomy feeds

The [Astronomy feeds](https://bsky.app/profile/emily.space/feed/astro) on [Bluesky](https://bsky.app/) are a set of 'custom algorithms' that collate astronomy content on Bluesky. This repository is one component of a multiple-service system to host the feeds.

## Installing the service

Create a fresh virtual environment with the Python version defined in runtime.txt. Then, install with `pip install -e .`.

Alternatively, you can use [uv](https://docs.astral.sh/uv/), which is now our preferred Python packaging tool.

## Running the app

You can start the webapp with the 'run' script, or the command

```
python -m astrobot
```

Note that it will sleep for ten minutes if it crashes, instead of restarting - this is a last-ditch way to try and prevent it from getting stuck in a spam-loop if something goes really wrong!