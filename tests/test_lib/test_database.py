import os
import subprocess
import peewee

from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from abc import ABC
from uuid import uuid4

from astrofeed_lib.database import Account, Post, BotActions, ModActions, proxy, DBConnection, setup_connection, teardown_connection
from astrofeed_lib.feeds import post_in_feeds


# sketch out a dataclass-based test database entry representation, to help keep track of
# required quantities to manually specify test database data (with some helper functions)
class testdb_entry(ABC):
    pass


@dataclass
class testdb_post_entry(testdb_entry):
    uri: str = "at://did:plc:AUTHOR_DID_XXXXXXXXXXXXX/app.bsky.feed.post/POST_XXXXXXXX"
    cid: str = "POST_CID_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    author: str = "did:plc:AUTHOR_DID_XXXXXXXXXXXXX"
    text: str = "text of post"
    feed_all: bool = True
    feed_astro: bool = False
    indexed_at: datetime = datetime.now(timezone.utc).replace(tzinfo=None) # column type is "timestamp without time zone"
    feed_exoplanets: bool = False
    feed_astrophotos: bool = False
    feed_cosmology: bool = False
    feed_extragalactic: bool = False
    feed_highenergy: bool = False
    feed_instrumentation: bool = False
    feed_methods: bool = False
    feed_milkyway: bool = False
    feed_planetary: bool = False
    feed_radio: bool = False
    feed_stellar: bool = False
    feed_education: bool = False
    feed_history: bool = False
    hidden: bool = False
    likes: int = 0
    feed_research: bool = False
    feed_solar: bool = False
    feed_questions: bool = False

@dataclass
class testdb_account_entry(testdb_entry):
    handle: str = "handle.domain"
    submission_id: str = ""
    did: str = "did:plc:ACCOUNT_DID_XXXXXXXXXXXX"
    is_valid: bool = True
    feed_all: bool = True
    indexed_at: datetime = datetime.now(timezone.utc).replace(tzinfo=None) # column type is "timestamp without time zone"
    mod_level: int = 0
    is_muted: bool = False
    is_banned: bool = False
    hidden_count: int = 0
    muted_count: int = 0
    banned_count: int = 0
    warned_count: int = 0

@dataclass
class testdb_modaction_entry(testdb_entry):
    indexed_at: datetime = datetime.now(timezone.utc).replace(tzinfo=None) # column type is "timestamp without time zone"
    did_mod: str = "did:plc:MOD_DID_XXXXXXXXXXXXXXXX"
    did_user: str = "did:plc:USER_DID_XXXXXXXXXXXXXXX"
    action: str = "type of mod action"  # signup, signup_cancelled, hide
    expiry: datetime = None # only column i've seen so far that can be null


@dataclass
class testdb_botaction_entry(testdb_entry):
    indexed_at: datetime = datetime.now(timezone.utc).replace(tzinfo=None) # column type is "timestamp without time zone"
    did: str = "did:plc:SUBJECT_DID_XXXXXXXXXXXX"
    type: str = "type of bot action"  # signup, joke, hide, unrecognized
    stage: str = "completion state"  # initial, rules_sent, get_description, get_moderator, complete
    parent_uri: str = (
        "at://did:plc:INITIATING_AUTHOR_DID_XX/app.bsky.feed.post/FIRST_POST_XX"
    )
    parent_cid: str = "INITIATING_POST_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    latest_uri: str = (
        "at://did:plc:COMPLETING_AUTHOR_DID_XX/app.bsky.feed.post/FINAL_POST_XX"
    )
    latest_cid: str = "COMPLETING_POST_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    complete: bool = True
    authorized: bool = True
    checked_at: datetime = datetime.now(timezone.utc).replace(tzinfo=None) # column type is "timestamp without time zone"


def generate_testdb_signup_entries(
    added_account: testdb_account_entry, mod_account: testdb_account_entry
):
    # one mod action per signup, to approve
    modaction = testdb_modaction_entry(
        did_mod=mod_account.did, did_user=added_account.did, action="signup"
    )
    # one bot action (multistep, continously updated throughout) per signup,
    # with somewhat informative strings replacing URI and CID strings for
    # relevant signup command posts (which are not stored in Post table)
    initial_post_str = added_account.handle + "_INITIAL_SIGNUP_POST_" + 49 * "X"
    final_post_str = added_account.handle + "_FINAL_SIGNUP_POST_" + 49 * "X"
    botaction = testdb_botaction_entry(
        did=added_account.did,
        type="signup",
        stage="complete",
        parent_uri=f"at://{added_account.did}/app.bsky.feed.post/SIGNUPINITIAL",
        parent_cid=initial_post_str[:49],
        latest_uri="at://did:plc:hol3fzmh4guugasdolbpzwtk/app.bsky.feed.post/3lj4wtq4en52d/app.bsky.feed.post/XSIGNUPFINALX",
        latest_cid=final_post_str[:49],
    )
    return modaction, botaction


def generate_testdb_post_by_author(
    text: str,
    author: testdb_account_entry,
    hidden: bool = False,
    rkey: str | None = None,
    cid: str | None = None,
):
    """creates test database post entry by taking fields from given author entry"""
    if rkey is None:
        rkey = str(uuid4()).replace("-", "")[:13]
    if cid is None:
        cid = author.handle + "_" + rkey + "_CID_" + 49 * "X"
    return testdb_post_entry(
        uri=f"at://{author.did}/app.bsky.feed.post/{rkey}",
        cid=cid[:49],
        author=author.did,
        text=text,
        hidden=hidden,
    )


def populate_test_db(
    test_db_conn: peewee.DatabaseProxy,
    overwrite: bool = False,
):
    """refreshes data in a test database, via a passed-in connection"""
    ##
    ## MANUALLY SPECIFY TEST DATABASE DATA HERE
    ##
    # note: some entries (mod and bot actions associated with signup) will be automatically
    # generated after manual data entry
    # WARNING: while some logic will be checked below (each Post entry has an author that corresponds to
    # an Account entry, hidden post has a corresponding entry in ModActions that hid it, etc), this is imperfect,
    # and care should be taken to check things like this manually
    accounts = [
        testdb_account_entry(
            handle="Alice", did="did:plc:AAAAAAAAAAAAAAAAAAAAAAAA", mod_level=5
        ),
        testdb_account_entry(
            handle="Bob", did="did:plc:BBBBBBBBBBBBBBBBBBBBBBBB"
        ),
        testdb_account_entry(
            handle="Charlie", did="did:plc:CCCCCCCCCCCCCCCCCCCCCCCC"
        ),
    ]

    posts = [
        generate_testdb_post_by_author(
            text="astronomy is great!", author=accounts[0]
        ),
        generate_testdb_post_by_author(
            text="astronomy is neat!", author=accounts[1]
        ),
        generate_testdb_post_by_author(
            text="my latest work is being published in MNRAS ☄️",
            author=accounts[0],
        ),
        generate_testdb_post_by_author(
            text="oooooo i'm bein a little mean >:(",
            author=accounts[2],
            hidden=True,
        ),
        generate_testdb_post_by_author(
            text="stars and planets have formed!", author=accounts[1]
        ),
    ]

    modactions = [
        testdb_modaction_entry(
            did_mod=accounts[0].did, did_user=accounts[2].did, action="hide"
        )
    ]
    botactions = [
        testdb_botaction_entry(
            did=accounts[0].did, type="joke", stage="complete"
        )
    ]

    ##
    ## END OF MANUAL DATA SPECIFICATION
    ##

    data = {Post: [], Account: [], ModActions: [], BotActions: []}

    # make sure we have at least one mod account, convert account entries to dicts, and add
    # minimum set of mod and bot actions per account
    if (
        len(
            mod_accounts := [
                account for account in accounts if account.mod_level > 0
            ]
        )
        == 0
    ):
        raise ValueError(
            "build_test_db: manually specified account entries do not contain "
            "at least one entry with mod_level>0 (required for automatic ModActions entries)"
        )
    for i in range(len(accounts)):
        account = accounts[i]
        mod_account = mod_accounts[i % len(mod_accounts)]

        modaction, botaction = generate_testdb_signup_entries(
            added_account=account, mod_account=mod_account
        )
        data[Account].append(asdict(account))
        data[ModActions].append(asdict(modaction))
        data[BotActions].append(asdict(botaction))

    # posts must be from a registered account, and there must be a "hide" mod action for the
    # author if they are hidden; and they are updated with feed boolean info based on text
    account_dids = [account.did for account in accounts]
    modaction_user_dids = [modaction.did_user for modaction in modactions]
    for post in posts:
        if post.author not in account_dids:
            raise ValueError(
                "build_test_db: "
                f"manually specified Post entry has author {post.author}, "
                "which has no corresponding entry in the Account table."
            )
        if post.hidden and post.author not in modaction_user_dids:
            raise ValueError(
                "build_test_db: "
                f'manually specified Post entry (text="{post.text}") is hidden, '
                "but there is no corresponding ModActions entry for its author."
            )
        post_dict = asdict(post)
        post_dict.update(**post_in_feeds(post.text))

        data[Post].append(post_dict)

    # manually specified ModAction and BotAction entries currently have no logic checks
    # (considered whether ModAction did_user values should be in Account, but that is not
    # true of the production database --- around 10% of user dids are not in Account)
    for model, entries in [(ModActions, modactions), (BotActions, botactions)]:
        for entry in entries:
            data[model].append(asdict(entry))

    # connect to database and write
    for model, entries in data.items():
        with model.bind_ctx(test_db_conn):
            if overwrite:
                test_db_conn.drop_tables([model])
            with test_db_conn.atomic():
                test_db_conn.create_tables([model])
                model.insert_many(entries).execute()

def build_test_db(
    test_db_name: str,
) -> peewee.PostgresqlDatabase:
    """builds a very small test database, to be used in automated tests, on the currently active PostgreSQL server"""
    # extract connection details from the current PostgreSQL connection
    user, password, host, port = proxy.connect_params.values()
    dev_db_name = proxy.database

    # # database creation and setup cannot be done with Peewee; handle it in a bash script
    # subprocess.call(f"../scripts/sql/testdb/build_test_db {user} {password} {host} {port} {database_name} {test_database_name}")

    # # population can be done with peewee, keeping this now to maintain consistency with prior SQLite approach
    # populate_test_db_postgres(test_db_conn := peewee.PostgresqlDatabase(test_database_name, host=host, port=port, user=user, password=password))

    # build database connection URIs from these details
    dev_conn_uri=f"postgresql://{user}:{password}@{host}:{port}/{dev_db_name}?"
    test_conn_uri=f"postgresql://{user}:{password}@{host}:{port}/{test_db_name}?"

    # dump schema from the dev database and create our test database
    subprocess.call(f"pg_dump -d \"{dev_conn_uri}\" --schema-only --schema 'public' > ./testschema.sql", shell=True)
    with DBConnection():
        proxy.obj.execute_sql(f"CREATE DATABASE {test_db_name} OWNER {user};")
        proxy.obj.execute_sql(f"GRANT ALL ON DATABASE {test_db_name} TO {user}")

    # connect to test database and set up schema
    test_db_conn = peewee.PostgresqlDatabase(test_db_name, host=host, port=port, user=user, password=password)
    setup_connection(test_db_conn)
    test_db_conn.execute_sql("DROP SCHEMA IF EXISTS public CASCADE;")
    teardown_connection(test_db_conn)
    subprocess.call(f"psql -X -d {test_conn_uri} -f ./testschema.sql", shell=True)
    os.remove("./testschema.sql")

    return test_db_conn

def delete_test_db(
    test_database_name: str,
):
    """removes a test database by name (assuming proxy is not connected to that database)"""
    # because we don't have any schema creation or
    with DBConnection():
        proxy.obj.execute_sql(f"DROP DATABASE {test_database_name}")