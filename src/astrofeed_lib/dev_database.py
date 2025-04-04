import os
import peewee
import warnings

from .database import Account, Post, BotActions, ModActions, SubscriptionState


def build_dev_db(
    source_database_name: str = "dbdump.db",
    destination_database_name: str = "dev_db.db",
    overwrite_existing: bool = False,
    take_num: int = 50000,
    take_frac: float = 0.0,
    sampling_strategy: str = "last",
):
    """Sample from larger SQLite database to create smaller SQLite database, following schema from astrofeed_lib.database

    in:
        source_database_name: string representing path to source database
        destination_database_name: string representing path to developed database to create
        overwrite_existing: boolean indicating whether a pre-existing developer database should be replaced
        take_num: number of entries to take from Post table (mutually exclusive with take_frac)
        take_frac: fraction of entries to take from Post table (mutually exclusive with take_num)
        sampling_strategy: string indicating sampling strategy to use
    """
    #
    to_write = dict(
        {
            Post: None,
            Account: None,
            BotActions: None,
            ModActions: None,
            SubscriptionState: None,
        }
    )

    # setup database connections
    db_conn_source = peewee.SqliteDatabase(source_database_name)

    if os.path.isfile(destination_database_name):
        if overwrite_existing:
            warnings.warn(
                f"Found pre-existing file {destination_database_name}, and overwrite_existing=True: removing and replacing file."
            )
            os.remove(destination_database_name)
        else:
            raise FileExistsError(
                f"Found pre-existing file {destination_database_name}, and overwrite_existing=False: "
                "please select another name for new database; move, remove, or rename existing "
                "dev database; or re-run with argument 'overwrite_existing=True' to overwrite."
            )
    db_conn_destination = peewee.SqliteDatabase(destination_database_name)
    for model in to_write.keys():
        with model.bind_ctx(db_conn_destination):
            db_conn_destination.create_tables([model])

    # only two sampling strategies implemented, default to last n posts
    supported_sampling_strategies = ["first", "last"]
    if(sampling_strategy not in supported_sampling_strategies):
        warnings.warn(f"Sampling strategy must be one of {supported_sampling_strategies}; setting sampling_strategy='last'.")
        sampling_strategy = "last"

    # now we build a dictionary of data to write (in the form of lists of dicts)
    with Post.bind_ctx(db_conn_source):
        # make sure our take_num/take_frac make sense
        total_posts = Post.select().count()

        if(((take_num!=0) == (take_frac!=0)) or (take_num < 0 or take_frac < 0)):
            raise ValueError("must specify a positive (nonzero) value for only one of take_num or take_frac.")
        elif(take_num > 0):
            if(take_num > total_posts):
                warnings.warn(f"{take_num} Post entries requested, but only {total_posts} available. Setting take_num={total_posts}")
                take_num = total_posts
        else:
            if(take_frac > 1):
                warnings.warn("take_frac > 1.0, setting take_frac=1.0")
                take_frac = 1.0
            take_num = round(take_frac * total_posts)

        # initial sampling of Post
        match sampling_strategy:
            case "last":
                sampled_posts = list(
                    Post.select()
                    .order_by(Post.indexed_at.desc())
                    .limit(take_num)
                    .dicts()
                )
            case "first":
                sampled_posts = list(
                    Post.select()
                    .order_by(Post.indexed_at.asc())
                    .limit(take_num)
                    .dicts()
                )

        # set posts to write
        to_write[Post] = sampled_posts

    with ModActions.bind_ctx(db_conn_source):
        # next, we get the unique DIDs making those posts, as well as the DIDs of mods who interacted with those users
        user_dids = set([entry["author"] for entry in sampled_posts])
        mod_dids = set(
            ModActions.select(ModActions.did_mod).where(
                ModActions.did_user << user_dids
            )
        )

        # together, these DIDs tell us who we're interested in from each non-user table, and we can sample from ModActions
        dids = user_dids.union(mod_dids)
        sampled_modactions = list(
            ModActions.select().where(ModActions.did_user << dids).dicts()
        )

        # set to write
        to_write[ModActions] = sampled_modactions

    # BotActions and Account don't contribute additional sampling contraints, and both have a DID field, so we can
    # sample from them together
    for model in [Account, BotActions]:
        with model.bind_ctx(db_conn_source):
            to_write[model] = list(model.select().where(model.did << dids).dicts())

    # SubscriptionState seems to always be a single entry, so we can just move that over as is
    with SubscriptionState.bind_ctx(db_conn_source):
        to_write[SubscriptionState] = list(SubscriptionState.select().dicts())

    # now, we write everything!
    for model, data in to_write.items():
        with model.bind_ctx(db_conn_destination):
            with db_conn_destination.atomic():
                for batch in peewee.chunked(data, 100):
                    model.insert_many(batch).execute()