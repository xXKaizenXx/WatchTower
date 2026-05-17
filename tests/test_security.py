from app.core.security import (
    generate_ping_token,
    hash_ping_token,
    verify_api_key,
    verify_ping_token,
)


def test_ping_token_roundtrip():
    token = generate_ping_token()
    hashed = hash_ping_token(token)
    assert verify_ping_token(token, hashed)
    assert not verify_ping_token("wrong", hashed)


def test_api_key_verification():
    assert verify_api_key("secret", "secret")
    assert not verify_api_key("wrong", "secret")
    assert not verify_api_key(None, "secret")
