# astrofeed-server

Configured Flask webapp for hosting the astronomy feeds.

## About the Astronomy feeds

The [Astronomy feeds](https://bsky.app/profile/emily.space/feed/astro) on [Bluesky](https://bsky.app/) are a set of 'custom algorithms' that collate astronomy content on Bluesky. This repository is one component of a multiple-service system to host the feeds.

## Installing the service

Create a fresh virtual environment with the Python version defined in runtime.txt. Then, install with `pip install -e .`.

## Running the app

You can start the webapp with the 'run' script, or the command

```
gunicorn --worker-tmp-dir /dev/shm src.astrofeed_server.app:app
```

## Running the app in development mode

You can also do `flask run` to run just a single Flask instance of the app without the reverse proxy provided by gunicorn.
