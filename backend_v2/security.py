import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password minimal 8 karakter.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_value, digest_value = encoded.split("$", 1)
        salt = base64.b64decode(salt_value)
        expected = base64.b64decode(digest_value)
    except (ValueError, TypeError):
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(actual, expected)


def create_session_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_session_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
