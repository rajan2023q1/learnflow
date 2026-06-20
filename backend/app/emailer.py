"""Transactional email (NFR-06). The dev backend logs messages and keeps an
in-memory outbox that tests assert against; swap `_deliver` for SES/SendGrid
in production (§3.7)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import settings

logger = logging.getLogger("learnflow.email")


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str
    token: str | None = None


@dataclass
class Emailer:
    outbox: list[SentEmail] = field(default_factory=list)

    def _deliver(self, message: SentEmail) -> None:
        self.outbox.append(message)
        logger.info("EMAIL → %s | %s\n%s", message.to, message.subject, message.body)

    def send_verification_email(self, to: str, token: str) -> None:
        link = f"{settings.frontend_url}/verify-email?token={token}"
        self._deliver(
            SentEmail(
                to=to,
                subject="Verify your LearnFlow email",
                body=(
                    "Welcome to LearnFlow! Confirm your email address to activate your "
                    f"account:\n\n{link}\n\nThis link expires in "
                    f"{settings.email_verification_ttl_hours} hours."
                ),
                token=token,
            )
        )

    def send_password_reset_email(self, to: str, token: str) -> None:
        link = f"{settings.frontend_url}/reset-password?token={token}"
        self._deliver(
            SentEmail(
                to=to,
                subject="Reset your LearnFlow password",
                body=(
                    "We received a request to reset your password. Set a new one here:\n\n"
                    f"{link}\n\nThis link expires in {settings.password_reset_ttl_hours} hour(s). "
                    "If you didn't request this, you can safely ignore this email."
                ),
                token=token,
            )
        )

    def send_lockout_warning(self, to: str) -> None:
        self._deliver(
            SentEmail(
                to=to,
                subject="Your LearnFlow account was temporarily locked",
                body=(
                    "We detected several failed sign-in attempts and have temporarily locked "
                    f"your account for {settings.lockout_minutes} minutes as a precaution. "
                    "If this wasn't you, please reset your password."
                ),
            )
        )

    def send_security_alert(self, to: str) -> None:
        self._deliver(
            SentEmail(
                to=to,
                subject="Security alert: unusual session activity",
                body=(
                    "We detected reuse of an expired session token on your LearnFlow account "
                    "and signed out all sessions as a precaution. Please log in again, and "
                    "reset your password if you don't recognise this activity."
                ),
            )
        )


# Module-level dev/test backend. NOTE: the in-memory `outbox` is per-process, so
# it is only meaningful with a single worker (tests, local dev). In production,
# replace `_deliver` with a real provider (SES/SendGrid) — outbox is not used.
emailer = Emailer()
