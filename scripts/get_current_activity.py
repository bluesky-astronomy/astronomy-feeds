"""A simple script just to fetch current bot activity to look at."""

from astrofeed_lib.database import BotActions


print(
    len(
        BotActions.select()
        .where(BotActions.complete == False, BotActions.type == "signup")  # noqa: E712
        .execute()
    )
)
