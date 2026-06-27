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

## Database migrations (Alembic)

Tables auto-create on startup in dev (`DB_AUTO_CREATE=true`). For managed
environments, set `DB_AUTO_CREATE=false` and drive the schema with Alembic:

```bash
alembic upgrade head                       # apply migrations
alembic revision --autogenerate -m "..."   # after changing models
```

The migration env reads `DATABASE_URL` and converts the async driver to its
sync equivalent automatically (`migrations/env.py`).

## Tests

```bash
pytest            # 43 tests, mapped to the UC-1 acceptance criteria
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

## UC-1 — Authentication & Identity Management

UC-1 is the learner identity lifecycle: self-registration with email verification,
credential login with short-lived RS256 access tokens and rotating refresh tokens,
explicit logout, account lockout, and self-service password reset. The full
business requirements (user stories, acceptance criteria, FRs/NFRs) live in
[`../docs/UC-1-requirements.md`](../docs/UC-1-requirements.md); this backend
implements all of them. The API surface is documented at runtime under `/docs`
and `/redoc`, and a static copy of the spec is checked in at
[`../docs/openapi.json`](../docs/openapi.json).

### User-story coverage

| Story | Summary | Status | Where |
|-------|---------|--------|-------|
| US-001 | New learner self-registration | ✅ | `POST /auth/register` |
| US-002 | Duplicate-email prevention (409) | ✅ | `POST /auth/register` |
| US-003 | Email verification + resend | ✅ | `POST /auth/verify-email`, `/auth/verify-email/resend` |
| US-004 | Credential-based login | ✅ | `POST /auth/login` |
| US-005 | Persistent session via JWT | ✅ (server) | `GET /auth/me`; silent refresh in `../frontend` |
| US-006 | Secure logout | ✅ | `POST /auth/logout` |
| US-007 | Access-token issuance (RS256) | ✅ | `app/jwt_service.py` |
| US-008 | Refresh-token rotation + reuse detection | ✅ | `POST /auth/refresh` |
| US-009 | Password-reset request (always 200) | ✅ | `POST /auth/password-reset/request` |
| US-010 | Password-reset completion + session revocation | ✅ | `POST /auth/password-reset/confirm` |
| US-011 | Expired-reset-link notification (410) | ✅ | `POST /auth/password-reset/confirm` |

### Regenerating the OpenAPI spec

`docs/openapi.json` is generated from the running app definition. Regenerate it
after changing any route or schema:

```bash
cd backend
python -m scripts.export_openapi          # writes ../docs/openapi.json
```

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
