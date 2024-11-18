"""A simple script just to fetch current bot activity to look at."""

from astrofeed_lib.database import db, BotActions


print(
    len(
        BotActions.select()
        .where(BotActions.complete == False, BotActions.type == "signup")
        .execute()
    )
)
