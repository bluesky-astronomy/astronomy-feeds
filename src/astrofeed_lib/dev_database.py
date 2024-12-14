import os
import numpy
import pandas
import peewee

from datetime import datetime
from database import *

def get_db_as_dict(source : str, source_format : str = "parquet"):
    """ 
        given a string representing a source to read data from, and another string
        indicating the format of that source: produce a dictionary linking labels for 
        ingested tables to dataframes containing the entries in those tables

        in:
            source       : string specifying the location of data to read in
            source_format: string indicating format data is stored in

        out:
            db: dictionary with names of source tables as keys, and dataframes containing 
                those tables' data as values
            
    """

    # initial housekeeping
    source_formats  = ["parquet"]
    planned_formats = ["mysql"]
    source_format   = source_format.lower()


    # now we can build the dictionary!
    db = dict()

    match source_format:
        case "parquet":
            # assume we are given a directory of tablename.parquet files, or a single tablename.parquet file
            if os.path.isdir(source):
                for filename in os.listdir(source):
                    tablename = os.path.splitext(filename)[0]
                    db[tablename] = pandas.read_parquet(source + "/" + filename)
            else:
                tablename = os.path.splitext(source)
                db[tablename] = pandas.read_parquet(source)

        case _:
            # default case if nothing is matched --- haven't implenented the requested format
            if source_format in planned_formats:
                errmsg = f"dev_database/get_db_as_dict: {source_format} is not yet implemented, but it is planned for the future!\nFor now, please use one of the following: {source_formats}"
            else:
                errmsg = f"dev_database/get_db_as_dict: {source_format} not a supported format, please use one of the following: {source_formats}"
            raise NotImplementedError(errmsg)

    return db

def truncate_db(db : dict[str, pandas.DataFrame], take_num : int = 0, take_frac : float = 0, sampling : str = "last"):
    """ 
        given a database with Post, Account, ModActions, BotActions, and SubscriptionState tables, 
        return a truncated database by sampling from Post, then finding all entries in other tables 
        related to sampled Post entries

        in:
            db       : dictionary of table labels and corresponding dataframes
            take_num : number of Post entries to truncate to
            take_frac: fraction of Post entries to truncate to
            sampling : whether to take {first, last, random} take_num entries from Post

        out:
            trunc_db: output dictionary (same structure as input), with truncated Post data and relevant entries 
                      from other dataframes
            
    """

    # make sure our take_num/take_frac make sense
    if(((take_num!=0) == (take_frac!=0)) or (take_num < 0 or take_frac < 0)):
        raise ValueError(f"dev_database/truncate_db: must specify a positive (nonzero) value for only one of take_num or take_frac in the argument list.")
    elif(take_num > 0):
        total_posts = len(db["Post"])
        if(take_num > total_posts):
            print(f"dev_database/truncate_db: {take_num} Post entries requested, but only {total_posts} available. Setting take_num={total_posts}")
            take_num = total_posts
    else:
        if(take_frac > 1):
            print("dev_database/truncate_db: take_frac is > 1.0, setting take_frac=1.0")
            take_frac = 1.0
        take_num = round(take_frac*len(db["Post"]))

    # only three sampling strategies implemented, default to last n posts
    if(sampling not in ["first", "last", "random"]):
        print("dev_database/truncate_db: Sampling must be 'first', 'last', or 'random'; setting sampling='last'")
        sampling = "last"

    # initial sampling of Post
    trunc_db = dict()
    match sampling:
        case "last":
            icut = len(db["Post"]) - take_num
            trunc_db["Post"] = db["Post"].iloc[icut:]
        case "first":
            trunc_db["Post"] = db["Post"].iloc[:take_num]
        case "random":
            trunc_db["Post"] = db["Post"].sample(n=take_num)

    # next, we get unique user ids from those posts, and find which mod actions involved those users
    user_dids = set(trunc_db["Post"]["author"])
    trunc_db["ModActions"] = db["ModActions"][db["ModActions"]["did_user"].isin(user_dids)]

    # then, the full set of relevant DIDs are those user DIDs, and the DIDs of mods involved in those actions
    mod_dids = set(trunc_db["ModActions"]["did_mod"])
    dids = user_dids.union(mod_dids)

    # now with our full set of DIDs, we can retrieve all of the relevant data from the other tables
    trunc_db["ModActions"       ] = db["ModActions"       ][db["ModActions"]["did_user"].isin(dids)] # for mods on user end of mod actions
    trunc_db["BotActions"       ] = db["BotActions"       ][db["BotActions"]["did"     ].isin(dids)]
    trunc_db["Account"          ] = db["Account"          ][db["Account"   ]["did"     ].isin(dids)]
    trunc_db["SubscriptionState"] = db["SubscriptionState"] # no selection necessary here, it's only one entry (for now)

    return trunc_db

def clean_db(db : dict[str, pandas.DataFrame]):
    """ 
        given a database, return a copy of the database with type conversions applied and replacement values inserted, 
        where necessary

        in:
            db: input database, as a dictionary of table labels, and corresponding dataframes holding the data

        out:
            clean_db: output database (same structure as input), with conversions and corrections applied
            
    """

    clean_db = dict()

    # db will be a dict, with each key leading to a dataframe
    for table in db.keys():
        df = db[table]

        # loop through df columns, and swap old columns for new
        for column in df.columns:
            # different replacement needs for different columns
            match column:
                case "indexed_at":
                    replacement_label = "indexed_at"

                    # make copy of column in python date-time format
                    replacement_data = df["indexed_at"].dt.to_pydatetime()
                    replacement_data = pandas.Series(replacement_data, dtype=object)

                case "checked_at":
                    replacement_label = "checked_at"

                    # possibly will be all-zeroes entries that we can't convert correctly,
                    # replace those before conversion
                    date_strings = df["checked_at"]
                    for i in range(len(date_strings)):
                        if date_strings.iloc[i] == "0000-00-00 00:00:00":
                            date_strings.iloc[i] = "0001-01-01 00:00:01"

                    replacement_data = pandas.Series([datetime.strptime(date_strings.iloc[i], "%Y-%m-%d %H:%M:%S") for i in range(len(date_strings))])

                case _: # default
                    continue

            # reindex the dataframe to match the replacement data
            df = df.set_index(replacement_data.index)

            # swap columns
            column_loc = df.columns.get_loc(replacement_label)
            df = df.drop(replacement_label, axis=1)
            df.insert(column_loc, replacement_label, replacement_data)

        # now we can fill the new database
        clean_db[table] = df

    return clean_db

def batch_write_to_db(write_dict : dict[BaseModel, pandas.DataFrame]):
    """ 
        given database model classes and associated dataframes, efficiently enter the data from the dataframes into 
        the corresponding database tables using peewee

        in:
            write_dict: dictionary associating classes (representing models/tables in a database) with dataframes 
                        containing entries that should be entered into the database            

    """

    for model,df in zip(write_dict.keys(), write_dict.values()):
        # get database from model (and perform final security check before writing...
        # REALLY don't want to be accessing the production database here):
        db = model._meta.db
        if type(db) is peewee.MySQLDatabase:
            raise ConnectionRefusedError("dev_database/batch_write_to_db: trying to write with a MySQL database connection, aborting.")

        # get the fields from the model
        model_fields = list(model._meta.fields.values())

        # atomic batched write
        with db.atomic():
            for batch in peewee.chunked(df.iloc[:,:].itertuples(index=False), 100):
                model.insert_many(rows=batch, fields=model_fields).execute()