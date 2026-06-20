"""Pydantic request/response models with the AC-001-03 password policy enforced
at the edge so invalid submissions are rejected with field-level 422 errors."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from .security import PASSWORD_RULE_MESSAGE, password_is_compliant


def _check_password(value: str) -> str:
    if not password_is_compliant(value):
        raise ValueError(PASSWORD_RULE_MESSAGE)
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return _check_password(v)

    @model_validator(mode="after")
    def _passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # When false, the refresh cookie is session-scoped (cleared on browser close).
    remember: bool = True


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return _check_password(v)

    @model_validator(mode="after")
    def _passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires


class MessageResponse(BaseModel):
    message: str


class RegisterResponse(BaseModel):
    message: str
    # True when the account was auto-verified (dev, no email provider) so the
    # client can route straight to login instead of the "check your inbox" screen.
    email_verified: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    email_verified: bool
    roles: list[str]
    created_at: datetime
