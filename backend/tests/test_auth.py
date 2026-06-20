"""End-to-end tests mapped to the UC-1 acceptance criteria."""

from __future__ import annotations

import pytest

from tests.conftest import GOOD_PASSWORD, register_and_verify, register_user


# --- Registration (US-001/002/003) -----------------------------------------
async def test_register_returns_201_and_sends_verification_email(client, outbox):
    resp = await register_user(client)
    assert resp.status_code == 201  # AC-001-01
    assert len(outbox) == 1 and outbox[0].token  # AC-001-02


async def test_duplicate_email_returns_409(client):
    await register_user(client)
    resp = await register_user(client)
    assert resp.status_code == 409  # AC-002-01
    assert resp.json()["detail"] == "An account with this email already exists"


@pytest.mark.parametrize("bad", ["Shor1!", "alllowercase1!", "NoNumber!", "NoSpecial1A"])
async def test_weak_password_rejected_422(client, bad):
    # AC-001-03 — policy enforced at the schema edge.
    resp = await client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": bad, "confirm_password": bad},
    )
    assert resp.status_code == 422


async def test_password_mismatch_rejected_422(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": GOOD_PASSWORD, "confirm_password": "Different1!"},
    )
    assert resp.status_code == 422


# --- Email verification (US-003) -------------------------------------------
async def test_verify_email_success(client, outbox):
    await register_user(client)
    resp = await client.post("/auth/verify-email", json={"token": outbox[-1].token})
    assert resp.status_code == 200  # AC-003-01


async def test_verify_email_invalid_token(client):
    resp = await client.post("/auth/verify-email", json={"token": "nope"})
    assert resp.status_code == 400


# --- Login (US-004) ---------------------------------------------------------
async def test_login_success_sets_refresh_cookie(client, outbox):
    email, password = await register_and_verify(client, outbox)
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200  # AC-004-01
    body = resp.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    assert "lf_refresh" in resp.cookies


async def test_login_wrong_password_401_generic(client, outbox):
    email, _ = await register_and_verify(client, outbox)
    resp = await client.post("/auth/login", json={"email": email, "password": "Wrong1!aa"})
    assert resp.status_code == 401  # AC-004-02
    assert resp.json()["detail"] == "Invalid email or password"


async def test_login_unverified_email_403(client):
    await register_user(client, email="unverified@example.com")
    resp = await client.post(
        "/auth/login", json={"email": "unverified@example.com", "password": GOOD_PASSWORD}
    )
    assert resp.status_code == 403  # AC-004-03


async def test_account_lockout_after_five_failures(client, outbox):
    email, password = await register_and_verify(client, outbox)
    for _ in range(5):
        r = await client.post("/auth/login", json={"email": email, "password": "Wrong1!aa"})
        assert r.status_code == 401
    # 6th attempt — even with the CORRECT password — is locked out (AC-004-04).
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 429
    assert any("locked" in m.subject.lower() for m in outbox)


# --- Protected route & JWT guard (US-005, US-007) ---------------------------
async def test_me_requires_token(client):
    assert (await client.get("/auth/me")).status_code == 401  # AC-007-02


async def test_me_with_token(client, outbox):
    email, password = await register_and_verify(client, outbox)
    login = await client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200  # AC-005-01
    assert resp.json()["email"] == email and resp.json()["roles"] == ["learner"]


async def test_me_rejects_tampered_token(client, outbox):
    email, password = await register_and_verify(client, outbox)
    login = await client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"] + "x"
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401  # AC-007-02


# --- Refresh rotation + reuse detection (US-008) ----------------------------
async def test_refresh_rotates_token(client, outbox):
    email, password = await register_and_verify(client, outbox)
    await client.post("/auth/login", json={"email": email, "password": password})
    old_cookie = client.cookies.get("lf_refresh")
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 200  # AC-008-01
    assert client.cookies.get("lf_refresh") != old_cookie  # rotated


async def test_refresh_reuse_detected_revokes_family(client, outbox):
    email, password = await register_and_verify(client, outbox)
    await client.post("/auth/login", json={"email": email, "password": password})
    stolen = client.cookies.get("lf_refresh")
    await client.post("/auth/refresh")  # rotate — `stolen` is now revoked

    # Replaying the old token triggers reuse detection (AC-008-02).
    resp = await client.post("/auth/refresh", cookies={"lf_refresh": stolen})
    assert resp.status_code == 401
    assert any("security" in m.subject.lower() for m in outbox)

    # The current (rotated) token is also dead now — whole family revoked.
    assert (await client.post("/auth/refresh")).status_code == 401


# --- Logout (US-006) --------------------------------------------------------
async def test_logout_revokes_refresh(client, outbox):
    email, password = await register_and_verify(client, outbox)
    await client.post("/auth/login", json={"email": email, "password": password})
    assert (await client.post("/auth/logout")).status_code == 200  # AC-006-01
    assert (await client.post("/auth/refresh")).status_code == 401


# --- Password reset (US-009/010/011) ----------------------------------------
async def test_password_reset_request_always_200(client):
    # Unknown email must not leak existence (FR-09 / AC-009-01).
    resp = await client.post("/auth/password-reset/request", json={"email": "ghost@example.com"})
    assert resp.status_code == 200


async def test_password_reset_completes_and_revokes_sessions(client, outbox):
    email, password = await register_and_verify(client, outbox)
    await client.post("/auth/login", json={"email": email, "password": password})

    await client.post("/auth/password-reset/request", json={"email": email})
    reset_token = outbox[-1].token
    new_password = "Brand0New!pw"
    resp = await client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "password": new_password, "confirm_password": new_password},
    )
    assert resp.status_code == 200  # AC-010-01

    # Old refresh token no longer works (AC-010-02).
    assert (await client.post("/auth/refresh")).status_code == 401
    # New password logs in.
    relogin = await client.post("/auth/login", json={"email": email, "password": new_password})
    assert relogin.status_code == 200


async def test_password_reset_invalid_token_400(client):
    resp = await client.post(
        "/auth/password-reset/confirm",
        json={"token": "bad", "password": GOOD_PASSWORD, "confirm_password": GOOD_PASSWORD},
    )
    assert resp.status_code == 400


# --- Review-fix regressions -------------------------------------------------
async def test_remember_me_false_sets_session_cookie(client, outbox):
    email, password = await register_and_verify(client, outbox)
    resp = await client.post(
        "/auth/login", json={"email": email, "password": password, "remember": False}
    )
    assert resp.status_code == 200
    set_cookie = " ".join(resp.headers.get_list("set-cookie")).lower()
    assert "lf_refresh=" in set_cookie
    assert "max-age" not in set_cookie  # session cookie — cleared on browser close


async def test_remember_me_true_sets_persistent_cookie(client, outbox):
    email, password = await register_and_verify(client, outbox)
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    set_cookie = " ".join(resp.headers.get_list("set-cookie")).lower()
    assert "max-age" in set_cookie  # persistent cookie


async def test_email_endpoint_is_throttled(client):
    # email_throttle_max defaults to 5 → the 6th request from one IP is rejected.
    for _ in range(5):
        r = await client.post("/auth/password-reset/request", json={"email": "x@example.com"})
        assert r.status_code == 200
    r = await client.post("/auth/password-reset/request", json={"email": "x@example.com"})
    assert r.status_code == 429
