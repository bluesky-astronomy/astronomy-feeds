"""Script for checking how DID updating went."""
from astrofeed_lib.accounts import Account
import pickle


query = Account.select()

handles, dids = [x.handle for x in query], [x.did for x in query]
n_accounts = len(handles)

handle_did_map = {h: d for h, d in zip(handles, dids)}


with open("handles.pickle", 'rb') as file:
    updated_handles = pickle.load(file)

with open("dids.pickle", 'rb') as file:
    updated_dids = pickle.load(file)


def count_nones(some_dict):
    return sum([x is None for x in some_dict.values()])


print(n_accounts, len(updated_handles), len(updated_dids))
print(n_accounts, count_nones(updated_handles), count_nones(updated_dids))


# Work out how many handles have changed
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

print(n_accounts, matching_dids)
print("Not found:", not_found)
print("DID has changed:", did_change)
print("New DIDs vs old DIDs:")
for a_handle in did_change:
    print(handle_did_map[a_handle], updated_dids[a_handle], a_handle)
