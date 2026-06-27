"""/auth endpoints — registration, email verification, login, JWT refresh with
rotation + reuse detection, logout, and password reset. Behaviour follows the
acceptance criteria in docs/UC-1-requirements.md."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db, utcnow
from ..deps import UserContext, get_current_user
from ..emailer import emailer
from ..jwt_service import create_access_token
from ..models import (
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    RefreshToken,
    ThrottleHit,
    User,
)
from ..schemas import (
    ErrorResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from ..security import generate_token, hash_password, hash_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Deliberately generic so the response cannot be used to enumerate accounts.
INVALID_CREDENTIALS = "Invalid email or password"
LOCKED_MESSAGE = "Account temporarily locked. Try again in 15 minutes."


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Case-insensitive lookup of a user by email. Returns ``None`` when no
    account matches, so callers can branch without leaking existence to clients."""
    normalized = email.strip().lower()
    return (
        await db.execute(select(User).where(func.lower(User.email) == normalized))
    ).scalar_one_or_none()


def _client_ip(request: Request) -> str:
    """Client IP, honouring X-Forwarded-For only when explicitly behind a
    trusted proxy (the header is spoofable otherwise)."""
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _enforce_throttle(db: AsyncSession, bucket: str) -> None:
    """Anti-abuse limiter for unauthenticated email-sending endpoints. Records a
    hit and raises 429 once `bucket` exceeds the configured rate."""
    window_start = utcnow() - timedelta(minutes=settings.email_throttle_window_minutes)
    # Opportunistic prune of stale rows so the table stays bounded.
    await db.execute(delete(ThrottleHit).where(ThrottleHit.created_at < window_start))
    count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ThrottleHit)
                .where(ThrottleHit.bucket == bucket, ThrottleHit.created_at >= window_start)
            )
        ).scalar_one()
    )
    if count >= settings.email_throttle_max:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    db.add(ThrottleHit(bucket=bucket))


def _set_refresh_cookie(response: Response, raw_token: str, *, persistent: bool = True) -> None:
    """Write the opaque refresh token to the HttpOnly/Secure/SameSite cookie
    (NFR-05). With ``persistent=False`` it becomes a session cookie that the
    browser drops on close ("remember me" unchecked)."""
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_token,
        # Persistent → survives browser restarts; otherwise a session cookie
        # ("remember me" unchecked, AC: cleared on browser close).
        max_age=settings.refresh_token_ttl_days * 24 * 3600 if persistent else None,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh cookie (logout, or on any path that invalidates the
    presented token) using the same domain/path it was set with."""
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


async def _issue_refresh_token(
    db: AsyncSession, user: User, family_id: uuid.UUID | None = None
) -> str:
    """Persist a new refresh token (only its hash is stored) and return the raw
    value for the cookie. Pass ``family_id`` to keep a rotated token in the same
    lineage so reuse detection can revoke the whole family (AC-008-02)."""
    raw = generate_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family_id=family_id or uuid.uuid4(),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    return raw


async def _issue_session(
    db: AsyncSession, user: User, response: Response, *, persistent: bool = True
) -> TokenResponse:
    """Mint an access token + a fresh refresh-token family and set the cookie."""
    access_token, expires_in = create_access_token(
        user_id=user.id, email=user.email, roles=list(user.roles)
    )
    raw_refresh = await _issue_refresh_token(db, user)
    await db.commit()
    _set_refresh_cookie(response, raw_refresh, persistent=persistent)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    """Bulk-revoke every still-active token in a family in one statement."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


# --------------------------------------------------------------------------- #
# Registration  (US-001, US-002, US-003)
# --------------------------------------------------------------------------- #
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    summary="Register a new learner account",
    description=(
        "Create a learner account from an email and a confirmed, policy-compliant "
        "password (US-001, AC-001-01). The password must be at least 8 characters "
        "with an uppercase letter, a digit, and a special character (AC-001-03), and "
        "`confirm_password` must match. The email is stored normalised (trimmed, "
        "lower-cased) and the password is bcrypt-hashed (FR-10).\n\n"
        "Unless the server is in its dev auto-verify mode, the account is created "
        "with `email_verified = false` and a single-use verification link is emailed "
        "within 30 seconds (AC-001-02); the response's `email_verified` flag tells the "
        "client whether to show the \"check your inbox\" screen or route straight to login."
    ),
    responses={
        status.HTTP_201_CREATED: {
            "description": "Account created. A verification email was queued unless "
            "auto-verify is enabled.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "An account already exists for this email (AC-002-01).",
            "content": {
                "application/json": {
                    "example": {"detail": "An account with this email already exists"}
                }
            },
        },
        422: {
            "description": "Validation failed — malformed email, password fails the "
            "complexity policy, or the passwords do not match (AC-001-03).",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                }
            },
        },
    },
)
async def register(
    payload: RegisterRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Self-service registration (US-001/US-002/US-003).

    Rejects a duplicate email with 409 (AC-002-01), otherwise persists the user
    and — when email verification is required — dispatches a single-use
    verification link as a background task (AC-001-02)."""
    if await _get_user_by_email(db, payload.email) is not None:
        # AC-002-01
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Dev fallback when no email provider is configured (see settings.auto_verify_email).
    auto_verify = settings.auto_verify_email

    user = User(
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        email_verified=auto_verify,
        roles=["learner"],
    )
    db.add(user)
    await db.flush()  # assign user.id

    raw_token: str | None = None
    if not auto_verify:
        raw_token = generate_token()
        db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=utcnow() + timedelta(hours=settings.email_verification_ttl_hours),
            )
        )
    await db.commit()

    if raw_token is not None:
        # Dispatch out of the request path (AC-001-02 within 30s — NFR-06).
        background.add_task(emailer.send_verification_email, user.email, raw_token)
        return RegisterResponse(
            message="Registration successful. Check your inbox to verify your email.",
            email_verified=False,
        )

    return RegisterResponse(
        message="Registration successful. You can log in now.",
        email_verified=True,
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    """Confirm an email from its verification token (US-003).

    Marks the account verified and consumes the single-use token (AC-003-01).
    An unknown token is 400; a token past its 24-hour TTL is deleted and
    answered with 410 so the client can prompt for a fresh link (AC-003-02)."""
    record = (
        await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == hash_token(payload.token)
            )
        )
    ).scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link is invalid.",
        )

    if record.expires_at < utcnow():
        # AC-003-02 — expired link, delete and tell the client to request a new one.
        await db.delete(record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This verification link has expired. Request a new one.",
        )

    user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one()
    user.email_verified = True
    await db.delete(record)  # single-use
    await db.commit()
    return MessageResponse(message="Email verified. You can now log in.")


@router.post("/verify-email/resend", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Re-send a verification link for an unverified account (US-003).

    Rate-limited per client IP (429 when exceeded). Replaces any outstanding
    token and emails a new one only when the account exists and is unverified,
    but always returns the same uniform message so the response can't reveal
    whether the email is registered (FR-09)."""
    await _enforce_throttle(db, f"resend:ip:{_client_ip(request)}")

    user = await _get_user_by_email(db, payload.email)
    if user is not None and not user.email_verified:
        await db.execute(
            delete(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
        )
        raw_token = generate_token()
        db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=utcnow() + timedelta(hours=settings.email_verification_ttl_hours),
            )
        )
        await db.commit()
        background.add_task(emailer.send_verification_email, user.email, raw_token)
    else:
        await db.commit()  # persist the throttle hit even on the no-op branch

    # Uniform response regardless of account state (FR-09).
    return MessageResponse(
        message="If your account exists and is unverified, a new link has been sent."
    )


# --------------------------------------------------------------------------- #
# Login / lockout  (US-004, US-007)
# --------------------------------------------------------------------------- #
async def _recent_failures(db: AsyncSession, email: str, ip: str | None = None) -> int:
    """Count recent failed attempts for an account. Scoped to `ip` when given
    (AC-004-04), or across all IPs when ip is None (distributed-attack guard)."""
    window_start = utcnow() - timedelta(minutes=settings.failed_login_window_minutes)
    conditions = [
        func.lower(LoginAttempt.email) == email.strip().lower(),
        LoginAttempt.successful.is_(False),
        LoginAttempt.created_at >= window_start,
    ]
    if ip is not None:
        conditions.append(LoginAttempt.ip_address == ip)
    stmt = select(func.count()).select_from(LoginAttempt).where(*conditions)
    return int((await db.execute(stmt)).scalar_one())


async def _record_attempt(db: AsyncSession, email: str, ip: str, *, successful: bool) -> None:
    """Append one row to the login-attempt ledger that drives the FR-06 lockout."""
    db.add(LoginAttempt(email=email.strip().lower(), ip_address=ip, successful=successful))


async def _prune_login_attempts(db: AsyncSession) -> None:
    """Delete login-attempt rows past the retention window so the ledger stays
    bounded (opportunistic, runs on each login)."""
    cutoff = utcnow() - timedelta(hours=settings.login_attempt_retention_hours)
    await db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
    description=(
        "Verify credentials and, on success, return a short-lived RS256 access "
        "token (15-minute TTL) while setting the opaque refresh token as an "
        "HttpOnly/Secure/SameSite cookie via the `Set-Cookie` response header "
        "(AC-004-01, AC-007-01, NFR-05). Send `remember = false` to make the "
        "refresh cookie session-scoped (cleared on browser close).\n\n"
        "Failures return a single generic message so callers cannot tell whether "
        "the email exists (AC-004-02, FR-09). After repeated failures the account "
        "is temporarily locked and a warning email is sent (AC-004-04, FR-06)."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Authenticated. Returns the access token; the refresh "
            "token is set in an HttpOnly cookie via `Set-Cookie`.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Unknown email or wrong password — deliberately "
            "indistinguishable (AC-004-02).",
            "content": {
                "application/json": {"example": {"detail": INVALID_CREDENTIALS}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Credentials are correct but the email is not yet "
            "verified (AC-004-03).",
            "content": {
                "application/json": {
                    "example": {"detail": "Please verify your email before logging in"}
                }
            },
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Account temporarily locked after too many failed "
            "attempts (AC-004-04).",
            "content": {"application/json": {"example": {"detail": LOCKED_MESSAGE}}},
        },
        422: {
            "description": "Validation failed — malformed email or missing fields.",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                }
            },
        },
    },
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Credential login (US-004, US-007).

    Enforces the FR-06 lockout before checking credentials, returns a generic
    401 on bad credentials (AC-004-02), 403 for a correct-but-unverified account
    (AC-004-03), and 429 once the failure threshold is crossed (AC-004-04). On
    success it clears the failure ledger and issues an access token plus a fresh
    refresh-token family (AC-004-01)."""
    ip = _client_ip(request)
    await _prune_login_attempts(db)  # keep the ledger bounded (finding #11)
    user = await _get_user_by_email(db, payload.email)
    now = utcnow()

    # Already locked? (AC-004-04)
    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=LOCKED_MESSAGE)

    # Lock when failures from this IP (AC-004-04) OR across all IPs (anti-rotation)
    # cross their thresholds; warn the holder and reject this attempt.
    ip_failures = await _recent_failures(db, payload.email, ip)
    email_failures = await _recent_failures(db, payload.email)
    if ip_failures >= settings.max_failed_logins or email_failures >= settings.max_failed_logins_per_email:
        if user is not None:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            await db.commit()
            # Synchronous: this path raises, and background tasks attached before a
            # raised HTTPException would not be dispatched.
            emailer.send_lockout_warning(user.email)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=LOCKED_MESSAGE)

    # Verify credentials (constant generic error either way — AC-004-02).
    if user is None or not verify_password(payload.password, user.password_hash):
        await _record_attempt(db, payload.email, ip, successful=False)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS
        )

    # Correct credentials but unverified address (AC-004-03).
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in",
        )

    # Success — clear the account's failure ledger, drop any expired lock, issue a session.
    await db.execute(
        delete(LoginAttempt).where(
            func.lower(LoginAttempt.email) == user.email.lower(),
            LoginAttempt.successful.is_(False),
        )
    )
    user.locked_until = None
    return await _issue_session(db, user, response, persistent=payload.remember)


# --------------------------------------------------------------------------- #
# Refresh rotation + reuse detection  (US-008)
# --------------------------------------------------------------------------- #
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Rotate the refresh token and mint a new access token (US-008).

    Reads the refresh cookie, then on a valid, unexpired, unrevoked token
    revokes it and issues a replacement in the same family plus a new access
    token (AC-008-01). Presenting an already-rotated token signals theft: the
    whole family is revoked and a security alert is emailed (AC-008-02). Missing,
    unknown, or expired tokens return 401 and clear the cookie."""
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    record = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
        )
    ).scalar_one_or_none()

    if record is None:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Reuse of an already-rotated (revoked) token ⇒ likely theft (AC-008-02).
    if record.revoked_at is not None:
        await _revoke_family(db, record.family_id)
        await db.commit()
        user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one_or_none()
        if user is not None:
            emailer.send_security_alert(user.email)
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked. Please log in again.",
        )

    if record.expires_at < utcnow():
        record.revoked_at = utcnow()
        await db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one()

    # Rotate: revoke the presented token, mint a replacement in the same family.
    record.revoked_at = utcnow()
    new_raw = await _issue_refresh_token(db, user, family_id=record.family_id)
    access_token, expires_in = create_access_token(
        user_id=user.id, email=user.email, roles=list(user.roles)
    )
    await db.commit()
    _set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


# --------------------------------------------------------------------------- #
# Logout  (US-006)
# --------------------------------------------------------------------------- #
@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """End the current session (US-006).

    Revokes the presented refresh token if it is still active and clears the
    cookie (AC-006-01). Idempotent: a missing or already-revoked token still
    returns 200 so logout never fails for the client."""
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        record = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
            )
        ).scalar_one_or_none()
        if record is not None and record.revoked_at is None:
            record.revoked_at = utcnow()
            await db.commit()

    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out.")


# --------------------------------------------------------------------------- #
# Password reset  (US-009, US-010, US-011)
# --------------------------------------------------------------------------- #
@router.post("/password-reset/request", response_model=MessageResponse)
async def password_reset_request(
    payload: PasswordResetRequest,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Start a self-service password reset (US-009).

    Rate-limited per client IP. When the email matches an account, stores a
    hashed, 1-hour UUID v4 reset token and emails the link; otherwise does
    nothing visible. Always returns 200 with the same message to prevent email
    enumeration (AC-009-01, FR-09)."""
    await _enforce_throttle(db, f"reset:ip:{_client_ip(request)}")

    user = await _get_user_by_email(db, payload.email)
    if user is not None:
        # AC-009-01 mandates a UUID v4 reset token (kept distinct from the
        # token_urlsafe() used elsewhere by spec); stored only as a hash.
        raw_token = str(uuid.uuid4())
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=utcnow() + timedelta(hours=settings.password_reset_ttl_hours),
            )
        )
        await db.commit()
        background.add_task(emailer.send_password_reset_email, user.email, raw_token)
    else:
        await db.commit()  # persist the throttle hit even when the email is unknown

    # Always 200, whether or not the email exists (FR-09 / AC-009-01).
    return MessageResponse(
        message="If an account exists for this email, a reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def password_reset_confirm(
    payload: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Complete a password reset with a valid token (US-010, US-011).

    On a valid, unused, unexpired token, sets the new (policy-compliant)
    password, consumes the token, and revokes every active refresh token for the
    account so all sessions are forced to re-authenticate (AC-010-01/02, FR-08).
    An invalid or already-used token is 400; an expired one is deleted and
    answered with 410 (AC-011-01)."""
    record = (
        await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_token(payload.token)
            )
        )
    ).scalar_one_or_none()

    if record is None or record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This link is invalid or has already been used.",
        )

    if record.expires_at < utcnow():
        # AC-011-01 — expired link.
        await db.delete(record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This link has expired — request a new one.",
        )

    user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one()
    user.password_hash = hash_password(payload.password)

    # Invalidate every active session for the account in one statement
    # (FR-08 / AC-010-02).
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )

    await db.delete(record)  # single-use
    await db.commit()
    return MessageResponse(message="Password updated. Please log in.")


# --------------------------------------------------------------------------- #
# Current user  (AC-005-01, AC-007-02)
# --------------------------------------------------------------------------- #
@router.get("/me", response_model=UserResponse)
async def me(
    current: UserContext = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    """Return the authenticated user's profile (US-005).

    JWT-guarded via ``get_current_user``: a missing, expired, or tampered token
    yields 401 (AC-005-01, AC-007-02)."""
    user = (await db.execute(select(User).where(User.id == current.id))).scalar_one()
    return user
