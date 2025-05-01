import pytest
from atproto import IdResolver

import astrobot.commands.moderation.ban

class MockIdResolver(IdResolver):
    '''atproto IdResolver replacement that uses mock handle resolver to avoid network checks for handle resolution'''
    # class variable to store handle -> DID mappings; this needs to be a class (static) variable 
    # because the command creates its own instance of this class during execution, so we need to 
    # be able to modify this in a way that all instances (including as-yet-uncreated ones) will see
    handle_to_did = dict()

    def __init__(self, plc_url = None, timeout = None, cache = None, backup_nameservers = None):
        super().__init__(plc_url, timeout, cache, backup_nameservers)

        # replace our handle resolver's resolve method with one that uses our internal mappings
        self.handle.resolve = self.mock_resolve

    def add_mapping(self, handle: str, did: str):
        '''Adds a new handle -> DID entry into the local dictionary'''
        handle = handle.lower() # everything is done in lowercased strings for Bsky

        # if handle isn't already present or the DID is different, make the change
        if handle not in self.handle_to_did.keys() or self.handle_to_did[handle] != did:
            self.handle_to_did.update({handle:did})

    def remove_mapping_by_handle(self, handle: str):
        '''Removes an existing handle -> DID entry from the local dictionary'''
        handle = handle.lower()
        if handle in self.handle_to_did.keys():
            del self.handle_to_did[handle]
            

    def mock_resolve(self, handle):
        '''Behaves like HandleResolver.resolve, except uses internal mappings rather than network lookup
        
        Checks for presence of requested handle in dictionary keys first, and returns None if not present; 
        to avoid a KeyError and simply return None in the result of no match, to replicate behavior of 
        mocked method.
        '''
        if handle in self.handle_to_did.keys():
            return self.handle_to_did[handle]
        else:
            return None

@pytest.fixture(scope="function")
def mock_idresolver():
    '''replace each test's ban command's IdResolver with the mock class, and yield an instance to the test'''
    store_IdResolver = astrobot.commands.moderation.ban.IdResolver
    astrobot.commands.moderation.ban.IdResolver = MockIdResolver

    # send an instance of the mock class to the test so that it can easily add mappings as it needs
    yield MockIdResolver(timeout=30)

    # cleanup; put original IdResolver back
    astrobot.commands.moderation.ban.IdResolver = store_IdResolver