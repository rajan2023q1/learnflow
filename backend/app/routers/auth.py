"""/auth endpoints — registration, email verification, login, JWT refresh with
rotation + reuse detection, logout, and password reset. Behaviour follows the
acceptance criteria in docs/UC-1-requirements.md."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
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
    User,
)
from ..schemas import (
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
    normalized = email.strip().lower()
    return (
        await db.execute(select(User).where(func.lower(User.email) == normalized))
    ).scalar_one_or_none()


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_token,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


async def _issue_refresh_token(
    db: AsyncSession, user: User, family_id: uuid.UUID | None = None
) -> str:
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


async def _issue_session(db: AsyncSession, user: User, response: Response) -> TokenResponse:
    """Mint an access token + a fresh refresh-token family and set the cookie."""
    access_token, expires_in = create_access_token(
        user_id=user.id, email=user.email, roles=list(user.roles)
    )
    raw_refresh = await _issue_refresh_token(db, user)
    await db.commit()
    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    now = utcnow()
    tokens = (
        await db.execute(select(RefreshToken).where(RefreshToken.family_id == family_id))
    ).scalars().all()
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = now


# --------------------------------------------------------------------------- #
# Registration  (US-001, US-002, US-003)
# --------------------------------------------------------------------------- #
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
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
        emailer.send_verification_email(user.email, raw_token)  # AC-001-02
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
    payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
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
        emailer.send_verification_email(user.email, raw_token)

    # Uniform response regardless of account state (FR-09).
    return MessageResponse(
        message="If your account exists and is unverified, a new link has been sent."
    )


# --------------------------------------------------------------------------- #
# Login / lockout  (US-004, US-007)
# --------------------------------------------------------------------------- #
async def _recent_failures(db: AsyncSession, email: str, ip: str) -> int:
    window_start = utcnow() - timedelta(minutes=settings.failed_login_window_minutes)
    stmt = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            func.lower(LoginAttempt.email) == email.strip().lower(),
            LoginAttempt.ip_address == ip,
            LoginAttempt.successful.is_(False),
            LoginAttempt.created_at >= window_start,
        )
    )
    return int((await db.execute(stmt)).scalar_one())


async def _record_attempt(db: AsyncSession, email: str, ip: str, *, successful: bool) -> None:
    db.add(LoginAttempt(email=email.strip().lower(), ip_address=ip, successful=successful))


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    user = await _get_user_by_email(db, payload.email)
    now = utcnow()

    # Already locked? (AC-004-04)
    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=LOCKED_MESSAGE)

    # Too many recent failures → lock now, warn the holder, and reject the 6th try.
    if await _recent_failures(db, payload.email, ip) >= settings.max_failed_logins:
        if user is not None:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            await db.commit()
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

    # Success — clear failure ledger, drop any expired lock, issue a session.
    await _record_attempt(db, payload.email, ip, successful=True)
    await db.execute(
        delete(LoginAttempt).where(
            func.lower(LoginAttempt.email) == user.email.lower(),
            LoginAttempt.ip_address == ip,
            LoginAttempt.successful.is_(False),
        )
    )
    user.locked_until = None
    return await _issue_session(db, user, response)


# --------------------------------------------------------------------------- #
# Refresh rotation + reuse detection  (US-008)
# --------------------------------------------------------------------------- #
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
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
    payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    user = await _get_user_by_email(db, payload.email)
    if user is not None:
        raw_token = str(uuid.uuid4())  # AC-009-01: UUID v4, stored hashed
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=utcnow() + timedelta(hours=settings.password_reset_ttl_hours),
            )
        )
        await db.commit()
        emailer.send_password_reset_email(user.email, raw_token)

    # Always 200, whether or not the email exists (FR-09 / AC-009-01).
    return MessageResponse(
        message="If an account exists for this email, a reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def password_reset_confirm(
    payload: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
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

    # Invalidate every active session for the account (FR-08 / AC-010-02).
    now = utcnow()
    tokens = (
        await db.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
    ).scalars().all()
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = now

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
    user = (await db.execute(select(User).where(User.id == current.id))).scalar_one()
    return user
