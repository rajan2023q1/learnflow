"""Edge-case tests covering defensive branches: expired tokens, lockout,
proxy IP, crafted-JWT rejection, and JWT key management."""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

import jwt as pyjwt
import pytest
from sqlalchemy import update

from app import database, jwt_service
from app.config import settings
from app.database import utcnow
from app.models import EmailVerificationToken, PasswordResetToken, RefreshToken, User
from app.security import verify_password
from tests.conftest import GOOD_PASSWORD, register_and_verify, register_user


async def _set_columns(model, **values) -> None:
    async with database.SessionLocal() as db:
        await db.execute(update(model).values(**values))
        await db.commit()


# --- security ---------------------------------------------------------------
def test_verify_password_handles_malformed_hash():
    # bcrypt.checkpw raises on a non-bcrypt hash → handled as a mismatch.
    assert verify_password("whatever", "not-a-bcrypt-hash") is False


# --- main: health + lifespan ------------------------------------------------
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_lifespan_creates_tables():
    from app.main import app, lifespan

    async with lifespan(app):
        pass  # exercises db_auto_create → create_all()


# --- deps: crafted-token rejection ------------------------------------------
def _mint(sub: str) -> str:
    private_key, _ = jwt_service._load_keys()
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": sub,
            "email": "x@example.com",
            "roles": ["learner"],
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm=settings.jwt_algorithm,
    )


async def test_me_rejects_non_uuid_sub(client):
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {_mint('not-a-uuid')}"})
    assert r.status_code == 401


async def test_me_rejects_unknown_user(client):
    token = _mint(str(uuid.uuid4()))  # valid signature, no such user
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# --- auth router: defensive branches ----------------------------------------
async def test_register_auto_verify(client, monkeypatch):
    monkeypatch.setattr(settings, "auto_verify_email", True)
    r = await register_user(client, email="auto@example.com")
    assert r.status_code == 201 and r.json()["email_verified"] is True


async def test_verify_email_expired_410(client, outbox):
    await register_user(client, email="exp@example.com")
    token = outbox[-1].token
    await _set_columns(EmailVerificationToken, expires_at=utcnow() - timedelta(hours=1))
    r = await client.post("/auth/verify-email", json={"token": token})
    assert r.status_code == 410


async def test_login_already_locked_returns_429(client, outbox):
    email, password = await register_and_verify(client, outbox)
    await _set_columns(User, locked_until=utcnow() + timedelta(minutes=10))
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 429


async def test_refresh_invalid_cookie_401(client):
    r = await client.post("/auth/refresh", cookies={"lf_refresh": "bogus-value"})
    assert r.status_code == 401


async def test_refresh_expired_token_401(client, outbox):
    email, password = await register_and_verify(client, outbox)
    await client.post("/auth/login", json={"email": email, "password": password})
    await _set_columns(RefreshToken, expires_at=utcnow() - timedelta(days=1))
    r = await client.post("/auth/refresh")
    assert r.status_code == 401


async def test_login_uses_forwarded_for_when_trusted(client, outbox, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy", True)
    email, password = await register_and_verify(client, outbox)
    r = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
    )
    assert r.status_code == 200


async def test_reset_confirm_expired_410(client, outbox):
    email, _ = await register_and_verify(client, outbox)
    await client.post("/auth/password-reset/request", json={"email": email})
    token = outbox[-1].token
    await _set_columns(PasswordResetToken, expires_at=utcnow() - timedelta(hours=2))
    new = "Brand0New!pw"
    r = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "password": new, "confirm_password": new},
    )
    assert r.status_code == 410


async def test_reset_confirm_password_mismatch_422(client):
    r = await client.post(
        "/auth/password-reset/confirm",
        json={"token": "x", "password": GOOD_PASSWORD, "confirm_password": "Different1!"},
    )
    assert r.status_code == 422


# --- jwt_service: key management branches -----------------------------------
@pytest.fixture
def jwt_cache_reset():
    """Reset and restore the module-level key cache around a test."""
    orig = (jwt_service._private_key, jwt_service._public_key)
    jwt_service._private_key = None
    jwt_service._public_key = None
    yield
    jwt_service._private_key, jwt_service._public_key = orig


def test_load_keys_from_inline_settings(jwt_cache_reset, monkeypatch):
    priv, pub = jwt_service._generate_keypair()
    monkeypatch.setattr(settings, "jwt_private_key", priv)
    monkeypatch.setattr(settings, "jwt_public_key", pub)
    got_priv, got_pub = jwt_service._load_keys()
    assert got_priv == priv and got_pub == pub


def test_load_keys_production_without_keys_raises(jwt_cache_reset, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "jwt_private_key", None)
    monkeypatch.setattr(settings, "jwt_public_key", None)
    monkeypatch.setattr(settings, "jwt_private_key_path", str(tmp_path / "missing_priv.pem"))
    monkeypatch.setattr(settings, "jwt_public_key_path", str(tmp_path / "missing_pub.pem"))
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError):
        jwt_service._load_keys()


def test_load_keys_generates_when_absent(jwt_cache_reset, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "jwt_private_key", None)
    monkeypatch.setattr(settings, "jwt_public_key", None)
    priv_path = tmp_path / "gen" / "priv.pem"
    pub_path = tmp_path / "gen" / "pub.pem"
    monkeypatch.setattr(settings, "jwt_private_key_path", str(priv_path))
    monkeypatch.setattr(settings, "jwt_public_key_path", str(pub_path))
    monkeypatch.setattr(settings, "environment", "development")
    priv, pub = jwt_service._load_keys()
    assert "PRIVATE KEY" in priv and "PUBLIC KEY" in pub
    assert priv_path.exists() and pub_path.exists()
