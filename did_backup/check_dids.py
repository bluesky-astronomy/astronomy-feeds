"""Script for checking how DID updating went."""
from astrofeed_lib.accounts import Account
import pickle


query = Account.select()

n_accounts = len([x.handle for x in query])



with open("handles.pickle", 'rb') as file:
    updated_handles = pickle.load(file)

with open("dids.pickle", 'rb') as file:
    updated_dids = pickle.load(file)


def count_nones(some_dict):
    return sum([x is None for x in some_dict.values()])


print(n_accounts, len(updated_handles), len(updated_dids))
print(n_accounts, count_nones(updated_handles), count_nones(updated_dids))
