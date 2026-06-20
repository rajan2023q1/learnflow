"""FastAPI dependencies: DB session and the `get_current_user` JWT guard
(AC-005-01, AC-007-02)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .jwt_service import decode_access_token
from .models import User

# auto_error=False so a missing header yields our own 401 message, not FastAPI's.
_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class UserContext:
    id: uuid.UUID
    email: str
    roles: list[str]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS_ERROR

    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        raise _CREDENTIALS_ERROR

    # Confirm the subject still exists (handles deleted accounts).
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_ERROR

    return UserContext(id=user.id, email=user.email, roles=list(user.roles))
