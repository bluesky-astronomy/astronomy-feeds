from atmos.identity import is_valid_did

def test_did():

    assert is_valid_did("did:web:example.com")
    assert is_valid_did("did:plc:abc123")
    assert is_valid_did("") is False
    assert is_valid_did("did:asdfasdf") is False
