# astrofeed-lib
Common functions for working with the Astronomy feeds, including the database and feed spec, and multiple other helpful utilities.

## Developing

### Installing

1. Download the module with

```bash
git clone https://github.com/bluesky-astronomy/astrofeed-lib.git
```

2. Ensure that you have uv installed to manage Python (see the [development guide](https://github.com/bluesky-astronomy/development-guide))

3. Set up the environment variables (see below) - only necessary if you need database access.

**Mandatory for using any database-related functionality:**
* `BLUESKY_DATABASE` - either a path to an SQLite development database (if `ASTROFEED_PRODUCTION` is false), or a connection string for a remote MySQL database (if `ASTROFEED_PRODUCTION` is true.) The MySQL database connection string should have the format `mysql://USER:PASSWORD@HOST:PORT/NAME?ssl-mode=REQUIRED`.

**Mandatory in production:**
* `ASTROFEED_PRODUCTION` - set to True to instead connect to a remote MySQL database