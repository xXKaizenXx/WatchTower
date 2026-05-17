import hashlib
import secrets
from hmac import compare_digest


def generate_ping_token() -> str:
    return secrets.token_urlsafe(32)


def hash_ping_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_ping_token(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    return compare_digest(hash_ping_token(plain), hashed)


def verify_api_key(provided: str | None, expected: str) -> bool:
    if not provided:
        return False
    return compare_digest(provided, expected)
