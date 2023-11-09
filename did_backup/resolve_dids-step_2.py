"""Quick emergency script for updating DID documents as PDS changes happen."""
from astrofeed_lib.accounts import fetch_handles, fetch_dids
from astrofeed_lib.database import Account
import pickle


query = Account.select()

handles = [x.handle for x in query]
dids = [x.did for x in query]

updated_handles = fetch_handles(dids)

updated_dids = fetch_dids(handles)

print(handles, updated_handles)

print(dids, updated_dids)


with open("handles.pickle", 'wb') as file:
    pickle.dump(updated_handles, file)

with open("dids.pickle", 'wb') as file:
    pickle.dump(updated_dids, file)
