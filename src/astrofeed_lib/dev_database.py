import os
import numpy
import pandas
import peewee
import warnings

from datetime import datetime

from .database import Account, Post, BotActions, ModActions, SubscriptionState

##
## main class that contains logic/methods for interacting with developer database, and data source to truncate from
##
class DB():
    """Represents a database (including model classes and names), and store data in that database.

    class variables:
        supported_source_formats: list of formats we can read source data in
        supported_sampling_strategies: list of ways we can truncate source data

    instance_variables:
        models: dictionary of model names and their classes, reflective of production database
        data: dictionary of table names (model names), with data stored for those tables in this instance

    methods:
        populate_from_source: read data in from given source
        truncate: remove data according to given criteria
        clean: implement data cleaning/replacement procedures
        write: write stored data to model class database connection                        
    """

    # what is currently supported
    supported_source_formats      = ["parquet", "sqlite"]
    supported_sampling_strategies = ["first", "last", "random"]

    def __init__(self, db_conn: peewee.Database):
        # get our models, and set their database connections
        #
        # hard coding this structure for now, but could probably be introspected from production db
        self.models = dict({
            "Account"           : Account,
            "Post"              : Post,
            "BotActions"        : BotActions,
            "ModActions"        : ModActions,
            "SubscriptionState" : SubscriptionState
        })
        for model in self.models.values():
            setattr(model._meta, "database", db_conn)

        # make empty dictionary to hold dataframes
        self.data = dict()

    def populate_from_source(self, source: str, format: str = "parquet"):
        """Fill instance's dictionary of stored data from given source.

        For now, this method will demand that every model name in our database structure has a corresponding 
        source, since at the moment everything else is build assuming we have a 'complete' set of data.

        in:
            source: string locating a source of data to read in
            format: string indicating format of data at that source
        """

        format = format.lower()

        if(format not in self.supported_source_formats):
            raise NotImplementedError(f"dev_database/DB/populate_from_source: \
                                        {format} not a supported format, please use one of the following: \
                                        {self.supported_source_formats}")

        match format:
            case "parquet":
                # assume we are given a directory of tablename.parquet files that match our database structure
                if os.path.isdir(source):
                    for model_name in self.models.keys():
                        target_file = source + "/" + model_name + ".parquet"
                        if os.path.isfile(target_file):
                            self.data[model_name] = pandas.read_parquet(target_file)
                        else:
                            raise FileNotFoundError(f"dev_database/DB/populate_from_source: \
                                                      No source file found for {model_name} table (looking for {target_file}).\n \
                                                      Source directory must contain files for each of these tables: ({self.models.keys()})")
                else:
                    raise NotADirectoryError(f"dev_database/DB/populate_from_source: No such directory '{source}': expecting a directory.")

            case "sqlite":
                # assume we're given a pre-existing database that matches the schema defined in our model classes

                # first, make sure we're given a pre-existing database file
                if not os.path.isfile(source):
                    raise FileNotFoundError(f"dev_database/DB/populate_from_source: \
                                            Unable to find {source} file; must be a pre-existing SQLite database file.")
                try:
                    source_db_conn = peewee.SqliteDatabase(source)
                    source_tables = source_db_conn.get_tables()
                except peewee.DatabaseError as err:
                    print(f"dev_database/DB/populate_from_source: \
                          could not parse {source} as an SqLite database file.")
                    raise err

                # now check to make sure that the database is complete
                if set(source_tables) != set([table_name.lower() for table_name in self.models.keys()]):
                    raise RuntimeError(f"dev_database/DB/populate_from_source: \n\
                                            Database at {source} does not contain all necessary tables to populate a \n\
                                            new database (has {source_tables} tables, must have {self.models.keys()} tables).")

                # now we can try to transfer database data to our internal representation
                for model_name, model in self.models.items():
                    try:
                        with model.bind_ctx(source_db_conn):
                            self.data[model_name] = pandas.DataFrame(model.select().dicts())
                    except peewee.DatabaseError as err:
                        print(f"dev_database/DB/populate_from_source: \
                            {model} table from {source} database does not match defined schema.")
                        raise err

            case _:
                raise NotImplementedError(f"dev_database/DB/populate_from_source: \
                                            {format} not a supported format, please use one of the following: \
                                            {self.supported_source_formats}")

    def truncate(self, take_num : int = 0, take_frac : float = 0, sampling : str = "last"):
        """Reduce volume of stored data, by sampling given amount according to given strategy.

        For the moment, this is built assuming that we have a 'complete' database (all models have associated 
        dataframes of data), and the method itself demands that we at least have a Post table to initially 
        sample from.

        in:
            take_num: number (integer) of entries to take from Post table (mutually exclusive with take_frac)
            take_frac: fraction (float) of entries to take from Post table (mutually exclusive with take_num)
            sampling: string indicating sampling strategy to use            
        """

        # make sure our take_num/take_frac make sense
        if(((take_num!=0) == (take_frac!=0)) or (take_num < 0 or take_frac < 0)):
            raise ValueError(f"dev_database/DB/truncate: \
                               must specify a positive (nonzero) value for only one of take_num or take_frac.")
        elif(take_num > 0):
            total_posts = len(self.data["Post"])
            if(take_num > total_posts):
                warnings.warn(f"dev_database/DB/truncate: \
                       {take_num} Post entries requested, but only {total_posts} available. Setting take_num={total_posts}")
                take_num = total_posts
        else:
            if(take_frac > 1):
                warnings.warn("dev_database/DB/truncate: take_frac > 1.0, setting take_frac=1.0")
                take_frac = 1.0
            take_num = round(take_frac*len(self.data["Post"]))

        # only three sampling strategies implemented, default to last n posts
        if(sampling not in self.supported_sampling_strategies):
            warnings.warn(f"dev_database/DB/truncate: \
                            Sampling must be one of {self.supported_sampling_strategies}; setting sampling='last'.")
            sampling = "last"

        # initial sampling of Post
        match sampling:
            case "last":
                icut = len(self.data["Post"]) - take_num
                self.data["Post"] = self.data["Post"].iloc[icut:].reset_index(drop=True)
            case "first":
                self.data["Post"] = self.data["Post"].iloc[:take_num].reset_index(drop=True)
            case "random":
                self.data["Post"] = (self.data["Post"].sample(n=take_num)).reset_index(drop=True)

        # next, we get the unique DIDs making those posts, as well as the DIDs of mods who interacted with those users
        user_dids = set(self.data["Post"]["author"])
        mod_dids  = set(self.data["ModActions"][self.data["ModActions"]["did_user"].isin(user_dids)]["did_mod"])
        dids = user_dids.union(mod_dids)

        # now with our full set of DIDs, we can retrieve all of the relevant data from the other tables
        self.data["ModActions"       ] = self.data["ModActions"       ].loc[self.data["ModActions"]["did_user"].isin(dids)] # for mods on user end of mod actions
        self.data["BotActions"       ] = self.data["BotActions"       ].loc[self.data["BotActions"]["did"     ].isin(dids)]
        self.data["Account"          ] = self.data["Account"          ].loc[self.data["Account"   ]["did"     ].isin(dids)]
        self.data["SubscriptionState"] = self.data["SubscriptionState"] # no selection necessary here, it's only one entry (for now)

    def clean(self):
        """Reduce volume of stored data, by sampling given amount according to given strategy.

        At the moment, this is implemented column by column (multiple of our tables have 'indexed_at' columns that 
        all need to be handled in the same way), and is highly specific and sensitive to the exact structure of the 
        database, and format of input data.

        in:
            take_num: number (integer) of entries to take from Post table (mutually exclusive with take_frac)
            take_frac: fraction (float) of entries to take from Post table (mutually exclusive with take_num)
            sampling: string indicating sampling strategy to use            
        """
        # for each table in our list, create a copy of the data and modify (if needed)
        for table_name,df in self.data.items():
            # clean copied data column by column, as needed
            for column in df.columns:
                # different replacement needs for different columns
                match column:
                    case "indexed_at":
                        if(type(df["indexed_at"].iloc[0]) is datetime):
                            # no need to clean
                            continue
                        else:
                            replacement_label = "indexed_at"

                            # make copy of column in python date-time format
                            with warnings.catch_warnings(): # suppresses deprecation warnings from to_pydatetime
                                warnings.simplefilter("ignore")
                                replacement_data = df["indexed_at"].dt.to_pydatetime()
                            replacement_data = pandas.Series(replacement_data, dtype=object)

                    case "checked_at":
                        if(type(df["checked_at"].iloc[0]) is datetime):
                            # no need to clean
                            continue
                        else:
                            # replace possible all-zeroes entries that we can't convert first
                            date_strings = numpy.array(df["checked_at"])
                            replacement_label = "checked_at"
                            replacement_data = []
                            for i in range(len(date_strings)):
                                if date_strings[i] == "0000-00-00 00:00:00":
                                    date_strings[i] = "0001-01-01 00:00:01"
                                replacement_data.append(datetime.strptime(date_strings[i], "%Y-%m-%d %H:%M:%S"))

                            replacement_data = pandas.Series(replacement_data)

                    case _: # no cleaning needed
                        continue

                # reindex the dataframe to match the replacement data
                df = df.set_index(replacement_data.index)

                # swap columns
                column_loc = df.columns.get_loc(replacement_label)
                df = df.drop(replacement_label, axis=1)
                df.insert(column_loc, replacement_label, replacement_data)

                self.data[table_name] = df

    def write(self):
        """Enter data stored in this instance into the databases connected to by associated model classes.

        Data is batched, and databased accessed atomically, to speed up operation; batch size is set to 100, 
        because it seems that SQLite and maybe some other kinds of databases can only handle 100 entries at a 
        time through the 'insert_many' method.
        """
        # write data for each model
        for model_name,model in self.models.items():
            # get database from model, and perform final security check before writing...
            # REALLY don't want to be accessing the production database here. if we start 
            # also maintaining MySQL dev databases, can use other checks to distinguish
            db_conn = model._meta.database
            if type(db_conn) is peewee.MySQLDatabase:
                raise ConnectionRefusedError("dev_database/write: MySQL database connection detected during write, \
                                              might be trying to write to prodution database; aborting.")

            # make the table for our model in the database if it doesn't already exist
            if model_name not in db_conn.get_tables():
                db_conn.create_tables([model])

            # get data and fields for our model, and perform an atomic batched write
            df = self.data[model_name]    
            model_fields = list(model._meta.fields.values())
            with db_conn.atomic():
                for batch in peewee.chunked(df.iloc[:,:].itertuples(index=False), 100): # chunks of 100 for SQLite compatibility
                    model.insert_many(rows=batch, fields=model_fields).execute()

##
## main function to be used outside of this module
##

def build_dev_db(data_source: str, 
                 source_format: str = "parquet", 
                 database_engine: str = "sqlite", 
                 truncation_num: int = 50000,
                 truncation_frac: float = 0.0,
                 truncation_strat: str = "last",
                 database_name : str = "dev_db.db",
                 overwrite_existing: bool = False):
    """Build a smaller, developer-friendly database from source data.

    in:
        data_souce: string locating un-truncated data to read in
        source_format: string indicating format of data in source
        database_engine: string indicating which engine to use for the developer database
        truncation_num: number of entries in the Post table to truncate to
        truncation_frac: fraction of entries in the Post table to truncate to
        truncation_strat: strategy to use for truncation
        overwrite_existing: boolean indicating whether to overwrite a pre-existing database
    """
    # initialize database
    if(os.path.isfile(database_name)):
        if overwrite_existing:
            warnings.warn(f"Found pre-existing file {database_name}, and overwrite_existing=True: removing file.")
            os.remove(database_name)
        else:
            raise FileExistsError(f"Found pre-existing file {database_name}, and overwrite_existing=False:\n \
                                  please select another name for new database; move, remove, or rename existing \
                                  dev database; or re-run with argument 'overwrite_existing=True' to overwrite.")

    database_engine = database_engine.lower()
    match database_engine:
        case "sqlite":
            db_conn = peewee.SqliteDatabase(database_name)
        case _:
            raise NotImplementedError(f"dev_database/build_dev_db: {database_engine} not supported, sorry!")

    database = DB(db_conn)

    # populate and process our data
    database.populate_from_source(source=data_source, format=source_format)
    database.truncate(take_num=truncation_num, take_frac=truncation_frac, sampling=truncation_strat)
    database.clean()

    # write to database
    database.write()