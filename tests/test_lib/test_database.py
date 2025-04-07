import os
import peewee
import warnings

from dataclasses import dataclass, asdict
from abc import ABC
from uuid import uuid4

from astrofeed_lib.database import Account, Post, BotActions, ModActions
from astrofeed_lib.dev_database import build_dev_db
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
    text: str  = "text of post"
    hidden : bool = False
@dataclass
class testdb_account_entry(testdb_entry):
    handle : str = "handle.domain"
    did: str = "did:plc:ACCOUNT_DID_XXXXXXXXXXXX"
    is_valid : bool = True
    mod_level : int = 0
    submission_id : str = ""
@dataclass
class testdb_modaction_entry(testdb_entry):
    did_mod : str = "did:plc:MOD_DID_XXXXXXXXXXXXXXXX"
    did_user : str = "did:plc:USER_DID_XXXXXXXXXXXXXXX"
    action : str = "type of mod action"  # signup, signup_cancelled, hide
@dataclass
class testdb_botaction_entry(testdb_entry):
    did : str = "did:plc:SUBJECT_DID_XXXXXXXXXXXX"
    type : str = "type of bot action"  # signup, joke, hide, unrecognized
    stage : str = "completion state"  # initial, rules_sent, get_description, get_moderator, complete
    parent_uri : str = "at://did:plc:INITIATING_AUTHOR_DID_XX/app.bsky.feed.post/FIRST_POST_XX"
    parent_cid : str = "INITIATING_POST_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    latest_uri : str = "at://did:plc:COMPLETING_AUTHOR_DID_XX/app.bsky.feed.post/FINAL_POST_XX"
    latest_cid : str = "COMPLETING_POST_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    complete : bool = True

def generate_testdb_signup_entries(added_account : testdb_account_entry, mod_account : testdb_account_entry):
    # one mod action per signup, to approve
    modaction = testdb_modaction_entry(did_mod=mod_account.did, did_user=added_account.did, action="signup")
    # one bot action (multistep, continously updated throughout) per signup, 
    # with somewhat informative strings replacing URI and CID strings for 
    # relevant signup command posts (which are not stored in Post table)
    initial_post_str = added_account.handle + "_INITIAL_SIGNUP_POST_" + 49*"X"
    final_post_str = added_account.handle + "_FINAL_SIGNUP_POST_" + 49*"X"
    botaction = testdb_botaction_entry(
        did=added_account.did,
        type="signup",
        stage="complete",
        parent_uri=f"at://{added_account.did}/app.bsky.feed.post/SIGNUPINITIAL",
        parent_cid=initial_post_str[:49],
        latest_uri="at://did:plc:hol3fzmh4guugasdolbpzwtk/app.bsky.feed.post/3lj4wtq4en52d/app.bsky.feed.post/XSIGNUPFINALX",
        latest_cid=final_post_str[:49]
    )
    return modaction, botaction

def generate_testdb_post_by_author(
        text : str, 
        author : testdb_account_entry, 
        hidden : bool = False, 
        rkey : str | None = None, 
        cid : str | None = None
    ):
    """creates test database post entry by taking fields from given author entry"""
    if rkey is None:
        rkey = str(uuid4()).replace("-", "")[:13]
    if cid is None:
        cid = author.handle + "_" + rkey + "_CID_" + 49*"X"
    return testdb_post_entry(
        uri=f"at://{author.did}/app.bsky.feed.post/{rkey}",
        cid=cid[:49],
        author=author.did,
        text=text,
        hidden=hidden
    )


def build_test_db(
        database_name : str = "test_db.db",
        method : str = "create",
        sample_source : str = "dev_db.db",
        sample_size : int = 10,
        overwrite_existing: bool = False
):
    '''builds a very small (enough to be in the repo) test database, which can be used for unit tests'''
    # initialize database
    if(os.path.isfile(database_name)):
        if overwrite_existing:
            warnings.warn(f"Found pre-existing file {database_name}, and overwrite_existing=True: removing and replacing file.")
            os.remove(database_name)
        else:
            raise FileExistsError(f"Found pre-existing file {database_name}, and overwrite_existing=False: "\
                                  "please select another name for new database; move, remove, or rename existing " \
                                  "dev database; or re-run with argument 'overwrite_existing=True' to overwrite.")

    match method:
        case "create":
            ##
            ## MANUALLY SPECIFY TEST DATABASE DATA HERE
            ##
            # note: some entries (mod and bot actions associated with signup) will be automatically 
            # generated after manual data entry
            # WARNING: while some logic will be checked below (each Post entry has an author that corresponds to 
            # an Account entry, hidden post has a corresponding entry in ModActions that hid it, etc), this is imperfect, 
            # and care should be taken to check things like this manually
            accounts = [
                testdb_account_entry(handle="Alice",   did="did:plc:AAAAAAAAAAAAAAAAAAAAAAAA", mod_level=5),
                testdb_account_entry(handle="Bob",     did="did:plc:BBBBBBBBBBBBBBBBBBBBBBBB"), 
                testdb_account_entry(handle="Charlie", did="did:plc:CCCCCCCCCCCCCCCCCCCCCCCC")
            ]

            posts = [
                generate_testdb_post_by_author(text="astronomy is great!", author=accounts[0]),
                generate_testdb_post_by_author(text="astronomy is neat!", author=accounts[1]), 
                generate_testdb_post_by_author(text="my latest work is being published in MNRAS ☄️", author=accounts[0]), 
                generate_testdb_post_by_author(text="oooooo i'm bein a little mean >:(", author=accounts[2], hidden=True), 
                generate_testdb_post_by_author(text="stars and planets have formed!", author=accounts[1])
            ]

            modactions = [
                testdb_modaction_entry(did_mod=accounts[0].did, did_user=accounts[2].did, action="hide")
            ]
            botactions = [
                testdb_botaction_entry(did=accounts[0].did, type="joke", stage="complete")
            ]

            ##
            ## END OF MANUAL DATA SPECIFICATION
            ##

            data = {
                Post: [],
                Account: [],
                ModActions: [],
                BotActions: []
            }

            # make sure we have at least one mod account, convert account entries to dicts, and add 
            # minimum set of mod and bot actions per account
            if len(mod_accounts := [account for account in accounts if account.mod_level>0]) == 0:
                raise ValueError("build_test_db: manually specified account entries do not contain " \
                                 "at least one entry with mod_level>0 (required for automatic ModActions entries)")
            for i in range(len(accounts)):
                account = accounts[i]
                mod_account = mod_accounts[i % len(mod_accounts)]

                modaction, botaction = generate_testdb_signup_entries(added_account=account, mod_account=mod_account)
                data[Account].append(asdict(account))
                data[ModActions].append(asdict(modaction))
                data[BotActions].append(asdict(botaction))


            # posts must be from a registered account, and there must be a "hide" mod action for the
            # author if they are hidden; and they are updated with feed boolean info based on text
            account_dids = [account.did for account in accounts]
            modaction_user_dids = [modaction.did_user for modaction in modactions]
            for post in posts:
                if post.author not in account_dids:
                    raise ValueError("build_test_db: " \
                                     f"manually specified Post entry has author {post.author}, " \
                                    "which has no corresponding entry in the Account table.")
                if post.hidden and post.author not in modaction_user_dids:
                    raise ValueError("build_test_db: " \
                                    f"manually specified Post entry (text=\"{post.text}\") is hidden, " \
                                    "but there is no corresponding ModActions entry for its author.")
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
            test_db_conn = peewee.SqliteDatabase(database_name)
            for model, entries in data.items():
                with model.bind_ctx(test_db_conn):
                    with test_db_conn.atomic():
                        test_db_conn.create_tables([model])
                        model.insert_many(entries).execute()

        case "sample":
            build_dev_db(
                source_database_name=sample_source, 
                destination_database_name=database_name, 
                take_num=sample_size, 
                overwrite_existing=overwrite_existing
            )

        case _:
            raise NotImplementedError(f"{method} not implemented, sorry!")