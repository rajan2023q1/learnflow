"""RS256 access-token issuance and verification (NFR-04, AC-007).

Keys are loaded from inline PEM settings, then PEM files, and — only in a
non-production environment — auto-generated on first use so the app runs with
zero setup. Production must supply real, securely-stored keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from .config import settings

_private_key: str | None = None
_public_key: str | None = None


def _generate_keypair() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )
    return private_pem, public_pem


def _load_keys() -> tuple[str, str]:
    global _private_key, _public_key
    if _private_key and _public_key:
        return _private_key, _public_key

    if settings.jwt_private_key and settings.jwt_public_key:
        _private_key, _public_key = settings.jwt_private_key, settings.jwt_public_key
        return _private_key, _public_key

    priv_path = Path(settings.jwt_private_key_path)
    pub_path = Path(settings.jwt_public_key_path)
    if priv_path.exists() and pub_path.exists():
        _private_key = priv_path.read_text()
        _public_key = pub_path.read_text()
        return _private_key, _public_key

    if settings.environment == "production":
        raise RuntimeError(
            "RS256 keys not configured. Set JWT_PRIVATE_KEY/JWT_PUBLIC_KEY or generate "
            "keys via `python -m scripts.generate_keys` before running in production."
        )

    # Dev convenience: generate and persist an ephemeral keypair.
    private_pem, public_pem = _generate_keypair()
    priv_path.parent.mkdir(parents=True, exist_ok=True)
    priv_path.write_text(private_pem)
    pub_path.write_text(public_pem)
    _private_key, _public_key = private_pem, public_pem
    return _private_key, _public_key


def create_access_token(*, user_id: uuid.UUID, email: str, roles: list[str]) -> tuple[str, int]:
    """Return (jwt, expires_in_seconds). Payload carries sub/email/roles/iat/exp."""
    private_key, _ = _load_keys()
    now = datetime.now(timezone.utc)  # aware UTC — .timestamp() must be a true epoch
    expires_in = settings.access_token_ttl_minutes * 60
    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Verify signature/expiry/issuer. Raises jwt.PyJWTError on any problem."""
    _, public_key = _load_keys()
    return jwt.decode(
        token,
        public_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["exp", "iat", "sub"]},
    )
