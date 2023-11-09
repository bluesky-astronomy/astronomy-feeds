"""Now that we have DIDs, we can keep fetching updated ones while PDS changes roll out."""
from astrofeed_lib.accounts import fetch_handles, fetch_dids
from astrofeed_lib.database import Account
import pickle


# Get current user handles
with open("handles.pickle", 'rb') as file:
    handles = pickle.load(file)
handle_did_map = {v: k for k, v in handles.items()}

# Use them to fetch DIDs, and then get updated handles too for said DIDs
updated_dids = fetch_dids(list(handles.values()))
updated_handles = fetch_handles(list(updated_dids.values()))

with open("handles_latest.pickle", 'wb') as file:
    pickle.dump(updated_handles, file)

with open("dids_latest.pickle", 'wb') as file:
    pickle.dump(updated_dids, file)


# Work out how many handles have changed
def count_nones(some_dict):
    return sum([x is not None for x in some_dict.values()])


n_accounts = len(handles)
matching_dids = 0
not_found = []
did_change = []
for a_handle in handle_did_map:
    if updated_dids[a_handle] is None:
        not_found.append(a_handle)
        continue

    if updated_dids[a_handle] == handle_did_map[a_handle]:
        matching_dids += 1
    else:
        did_change.append(a_handle)

print("STATISTICS ON RUN")
print("TOTAL ACCOUNTS:", n_accounts, ", DIDs FOUND:", matching_dids, ", HANDLES_FOUND: ", count_nones(updated_handles))
print("DID not found:", not_found)
print("DID has changed:", did_change)
print("New DIDs vs old DIDs:")
for a_handle in did_change:
    print(handle_did_map[a_handle], updated_dids[a_handle], a_handle)
