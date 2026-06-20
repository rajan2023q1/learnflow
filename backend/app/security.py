"""Password hashing (FR-10), password-complexity policy (AC-001-03), and
opaque-token generation/hashing for verification / reset / refresh tokens."""

from __future__ import annotations

import hashlib
import re
import secrets

import bcrypt

from .config import settings

# Same complexity rule the React client enforces: ≥8 chars, 1 upper, 1 digit, 1 symbol.
_SPECIAL = r"[!@#$%^&*(),.?\":{}|<>_\-\[\]\\/+=;'`~]"
PASSWORD_RULE_MESSAGE = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a number, and a special character."
)


def password_is_compliant(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password) is not None
        and re.search(r"[0-9]", password) is not None
        and re.search(_SPECIAL, password) is not None
    )


def hash_password(password: str) -> str:
    """bcrypt with cost ≥ 12. Pre-hashed with SHA-256 so the 72-byte bcrypt
    input limit never silently truncates a long passphrase."""
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")
    return bcrypt.hashpw(digest, bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")
    try:
        return bcrypt.checkpw(digest, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def generate_token() -> str:
    """A high-entropy opaque token handed to the user (URL-safe)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only the SHA-256 of a token is stored, so a DB leak can't be replayed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
