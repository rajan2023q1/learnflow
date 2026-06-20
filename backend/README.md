# LearnFlow — Auth backend (FastAPI)

Implementation of **UC-1: Authentication & Identity Management**
([`../docs/UC-1-requirements.md`](../docs/UC-1-requirements.md)) — registration,
email verification, credential login, RS256 JWT issuance, refresh-token rotation
with reuse detection, logout, account lockout, and self-service password reset.

**Stack:** FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL 17 (SQLite for dev/tests)
· PyJWT (RS256) · bcrypt.

## Quick start

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # COOKIE_SECURE=false for local HTTP
uvicorn app.main:app --reload   # http://localhost:8000  ·  docs at /docs
```

No database setup is required by default — it uses a local SQLite file. Point
`DATABASE_URL` at Postgres for production:

```
DATABASE_URL=postgresql+asyncpg://learnflow:learnflow@localhost:5432/learnflow
```

RS256 keys auto-generate under `keys/` on first run in dev. For production,
generate them explicitly and store the private key in a secrets manager:

```bash
python -m scripts.generate_keys           # writes keys/jwt_{private,public}.pem
```

## Tests

```bash
pytest            # 22 tests, mapped to the UC-1 acceptance criteria
```

## Endpoints

| Method | Path | Purpose | Key ACs |
|--------|------|---------|---------|
| POST | `/auth/register` | Create account, send verification email | AC-001, AC-002 |
| POST | `/auth/verify-email` | Confirm email from token (410 if expired) | AC-003 |
| POST | `/auth/verify-email/resend` | Re-send verification (no enumeration) | US-003 |
| POST | `/auth/login` | Credential login → access JWT + refresh cookie | AC-004, AC-007 |
| POST | `/auth/refresh` | Rotate refresh token; detect reuse | AC-008 |
| POST | `/auth/logout` | Revoke refresh token, clear cookie | AC-006 |
| POST | `/auth/password-reset/request` | Always-200 reset request | AC-009 |
| POST | `/auth/password-reset/confirm` | Set new password, revoke sessions (410 if expired) | AC-010, AC-011 |
| GET | `/auth/me` | Current user (JWT-guarded) | AC-005, AC-007 |

## How the requirements map to code

- **Password policy (AC-001-03)** — `app/security.py::password_is_compliant`, enforced in `app/schemas.py`.
- **bcrypt ≥ 12 (FR-10)** — `app/security.py` (SHA-256 pre-hash avoids bcrypt's 72-byte limit).
- **RS256 JWT (NFR-04, AC-007)** — `app/jwt_service.py`; payload `sub/email/roles/iat/exp/iss`.
- **Refresh rotation + reuse detection (FR-05, AC-008)** — `app/routers/auth.py::refresh`. Rotated tokens are marked revoked (not deleted) so replay of an old token revokes the whole `family_id` and emails a security alert.
- **Account lockout (FR-06, AC-004-04)** — `login_attempts` ledger; 5 failures per (email, IP) in 10 min → 15-min lock + warning email.
- **No enumeration (FR-09)** — generic `401` on login, uniform `200` on reset/resend requests.
- **Session invalidation on reset (FR-08, AC-010-02)** — confirm revokes every refresh token for the user.
- **HttpOnly/Secure/SameSite cookie (NFR-05)** — `_set_refresh_cookie`.

## Notes / production hardening

- **Email** is a console/in-memory backend (`app/emailer.py`); wire SES/SendGrid for go-live.
- **Migrations** — tables are auto-created on startup for dev convenience; use Alembic in production.
- The `email_verified` redirect/banner (AC-003-01) and the silent-refresh client logic (AC-005-02) live in the React frontend (`../frontend`).
