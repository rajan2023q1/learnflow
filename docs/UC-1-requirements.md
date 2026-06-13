# LearnFlow — Authentication & Identity Management
**Document Type:** Business Requirements Document (Excerpt)
**Feature Area:** User Registration, Login, JWT Issuing, Password Reset
**Stack Context:** FastAPI · React 19 · PostgreSQL 17 · JWT (Bearer)
**Status:** Draft v1.0
**Date:** 2026-06-13

---

## 1. User Stories

### 1.1 Registration

**US-001 — New Learner Self-Registration**
> As a **prospective learner**,
> I want to **create an account with my email address and a password**,
> so that **I can access LearnFlow courses and track my progress**.

**US-002 — Duplicate Email Prevention**
> As a **prospective learner**,
> I want to **be notified immediately if my email is already registered**,
> so that **I know to log in or reset my password instead of creating a duplicate account**.

**US-003 — Email Verification**
> As a **newly registered learner**,
> I want to **verify my email address by clicking a link sent to my inbox**,
> so that **my account is confirmed and protected against unauthorised sign-ups**.

---

### 1.2 Login

**US-004 — Credential-Based Login**
> As a **registered learner**,
> I want to **log in with my email and password**,
> so that **I can access my personalised dashboard and enrolled courses**.

**US-005 — Persistent Session via JWT**
> As a **logged-in learner**,
> I want to **remain authenticated across page refreshes and short idle periods**,
> so that **I do not have to log in repeatedly during an active study session**.

**US-006 — Secure Logout**
> As a **logged-in learner**,
> I want to **log out of LearnFlow explicitly**,
> so that **my session is ended and my account is protected on shared devices**.

---

### 1.3 JWT Issuing

**US-007 — Access Token Issuance on Login**
> As the **LearnFlow API**,
> I want to **issue a short-lived JWT access token upon successful authentication**,
> so that **downstream services can verify user identity without querying the database on every request**.

**US-008 — Refresh Token Rotation**
> As a **logged-in learner**,
> I want to **receive a new access token automatically before mine expires**,
> so that **my session continues uninterrupted without requiring me to re-enter credentials**.

---

### 1.4 Password Reset

**US-009 — Self-Service Password Reset Request**
> As a **learner who has forgotten their password**,
> I want to **request a password reset link via my registered email**,
> so that **I can regain access to my account without contacting support**.

**US-010 — Password Reset Completion**
> As a **learner who received a reset link**,
> I want to **set a new password through a secure, time-limited form**,
> so that **my account is secured with credentials only I know**.

**US-011 — Reset Link Expiry Notification**
> As a **learner with an expired reset link**,
> I want to **be clearly informed that the link is no longer valid and prompted to request a new one**,
> so that **I am not left confused about why the reset failed**.

---

## 2. Acceptance Criteria

### 2.1 Registration

#### US-001 — New Learner Self-Registration

**AC-001-01**
- **Given** a visitor is on the `/register` page
- **When** they submit a valid email, a password meeting complexity rules, and a confirmed password that matches
- **Then** a new `users` record is created in PostgreSQL with a bcrypt-hashed password, `email_verified = false`, and an HTTP 201 response is returned

**AC-001-02**
- **Given** a successful registration submission
- **When** the record is persisted
- **Then** a verification email is dispatched to the provided address within 30 seconds containing a single-use token link

**AC-001-03**
- **Given** a password field on the registration form
- **When** the user enters a value
- **Then** the system enforces: minimum 8 characters, at least one uppercase letter, one digit, and one special character — rejecting submissions that do not meet all criteria with field-level error messages

#### US-002 — Duplicate Email Prevention

**AC-002-01**
- **Given** an email address already exists in the `users` table
- **When** a registration request is submitted with that email
- **Then** the API returns HTTP 409 with the message "An account with this email already exists" and no new record is created

**AC-002-02**
- **Given** the 409 error is returned
- **When** the React form renders the response
- **Then** the email field is highlighted with the error inline; no password data is echoed back

#### US-003 — Email Verification

**AC-003-01**
- **Given** a user clicks the verification link within 24 hours
- **When** the token is validated against the `email_verification_tokens` table
- **Then** `email_verified` is set to `true`, the token is deleted, and the user is redirected to `/login` with a success banner

**AC-003-02**
- **Given** a verification link older than 24 hours is clicked
- **When** the token is evaluated
- **Then** the API returns HTTP 410, the token is deleted, and the UI prompts the user to request a new verification email

---

### 2.2 Login

#### US-004 — Credential-Based Login

**AC-004-01**
- **Given** a registered user with `email_verified = true`
- **When** they submit correct credentials to `POST /auth/login`
- **Then** the API returns HTTP 200 with an access token (JWT, 15-min TTL) and a refresh token (opaque, 7-day TTL) set as an `HttpOnly` cookie

**AC-004-02**
- **Given** a user submits an incorrect password
- **When** the API evaluates the credentials
- **Then** HTTP 401 is returned with the generic message "Invalid email or password" — no indication of which field is wrong

**AC-004-03**
- **Given** a user submits correct credentials but `email_verified = false`
- **When** the API evaluates the login
- **Then** HTTP 403 is returned with the message "Please verify your email before logging in" and a link to resend verification

**AC-004-04**
- **Given** 5 consecutive failed login attempts from the same IP for the same account within 10 minutes
- **When** a sixth attempt is made
- **Then** the API returns HTTP 429, the account is temporarily locked for 15 minutes, and a warning email is sent to the account holder

#### US-005 — Persistent Session via JWT

**AC-005-01**
- **Given** a valid access token in the `Authorization: Bearer` header
- **When** any protected API endpoint is called
- **Then** the request is processed and a 401 is never returned solely due to missing identity

**AC-005-02**
- **Given** an access token with less than 2 minutes remaining
- **When** the React client detects expiry via the `exp` claim
- **Then** the client silently calls `POST /auth/refresh` using the `HttpOnly` refresh cookie and replaces the in-memory access token without user disruption

#### US-006 — Secure Logout

**AC-006-01**
- **Given** a logged-in user clicks "Log Out"
- **When** `POST /auth/logout` is called
- **Then** the refresh token is revoked in the `refresh_tokens` table, the `HttpOnly` cookie is cleared, the in-memory access token is discarded, and the user is redirected to `/login`

---

### 2.3 JWT Issuing

#### US-007 — Access Token Issuance

**AC-007-01**
- **Given** a successful login
- **When** the JWT access token is generated
- **Then** the token payload contains: `sub` (user UUID), `email`, `roles` (array), `iat`, `exp` (now + 15 min), and is signed with RS256 using the server's private key

**AC-007-02**
- **Given** a protected endpoint receives a JWT
- **When** the FastAPI `Depends(get_current_user)` guard evaluates it
- **Then** an expired, tampered, or missing token results in HTTP 401; a valid token resolves to the `UserContext` object

#### US-008 — Refresh Token Rotation

**AC-008-01**
- **Given** a valid refresh token cookie is presented to `POST /auth/refresh`
- **When** the token is found in `refresh_tokens` and is not expired or revoked
- **Then** the old refresh token is deleted, a new refresh token is stored, a new access token is issued, and HTTP 200 is returned

**AC-008-02**
- **Given** a refresh token is reused after rotation (potential token theft)
- **When** `POST /auth/refresh` is called with the old token
- **Then** the entire refresh token family for that user is revoked, all sessions are terminated, and a security alert email is sent to the user

---

### 2.4 Password Reset

#### US-009 — Password Reset Request

**AC-009-01**
- **Given** a user submits `POST /auth/password-reset/request` with a registered email
- **When** the request is processed
- **Then** a reset token (UUID v4, hashed in DB) is stored in `password_reset_tokens` with a 1-hour expiry and an email is sent — always returning HTTP 200 regardless of whether the email exists (prevents enumeration)

#### US-010 — Password Reset Completion

**AC-010-01**
- **Given** a user submits a new password and confirmation via `POST /auth/password-reset/confirm` with a valid token
- **When** the token is verified and passwords match and meet complexity rules
- **Then** the `users.password_hash` is updated, the token is deleted, all existing refresh tokens for the user are revoked, and HTTP 200 is returned

**AC-010-02**
- **Given** the reset is successful
- **When** the user attempts to use any previously issued refresh token
- **Then** `POST /auth/refresh` returns HTTP 401, forcing a fresh login

#### US-011 — Expired Reset Link

**AC-011-01**
- **Given** a reset token older than 1 hour is submitted
- **When** `POST /auth/password-reset/confirm` evaluates the token
- **Then** HTTP 410 is returned, the token is deleted, and the React UI displays "This link has expired — request a new one" with a direct link to `/forgot-password`

---

## 3. Business Requirements Document — Authentication Module

### 3.1 Purpose

This section defines the business requirements for the **LearnFlow Authentication & Identity Management** module. The goal is to enable secure, standards-compliant user identity management that supports learner access to all platform features while protecting user data and complying with applicable security standards.

### 3.2 Business Objectives

| ID | Objective |
|----|-----------|
| BO-1 | Enable learner self-service onboarding with zero support overhead for account creation |
| BO-2 | Minimise unauthorised account access through layered authentication controls |
| BO-3 | Maintain session continuity to reduce friction and improve course completion rates |
| BO-4 | Ensure the platform meets OWASP Top 10 authentication security requirements |
| BO-5 | Reduce password-related support tickets via self-service reset flows |

### 3.3 Scope

**In scope:**
- Email/password registration with verification
- Credential-based login with JWT access + refresh token issuance
- Token refresh and rotation
- Explicit logout and session termination
- Self-service password reset via email

**Out of scope (future phases):**
- OAuth 2.0 / Social login (Google, LinkedIn)
- Multi-factor authentication (MFA)
- Single Sign-On (SSO / SAML)
- Admin-initiated account creation

### 3.4 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall allow users to register using a unique email address and a compliant password | Must Have |
| FR-02 | The system shall verify user email addresses before permitting login | Must Have |
| FR-03 | The system shall authenticate users via email/password and issue a JWT access token and an opaque refresh token | Must Have |
| FR-04 | Access tokens shall be short-lived (15 minutes); refresh tokens shall expire after 7 days of inactivity | Must Have |
| FR-05 | The system shall rotate refresh tokens on every use and detect and respond to token reuse attacks | Must Have |
| FR-06 | The system shall enforce account lockout after 5 failed login attempts within 10 minutes | Must Have |
| FR-07 | The system shall provide a self-service password reset flow via a time-limited (1-hour) email link | Must Have |
| FR-08 | Password reset shall invalidate all active sessions for the affected account | Must Have |
| FR-09 | The system shall never return information that allows enumeration of registered email addresses | Must Have |
| FR-10 | Passwords shall be hashed with bcrypt (cost factor ≥ 12) before storage | Must Have |

### 3.5 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Login endpoint response time (p95) | < 400 ms |
| NFR-02 | Registration endpoint response time (p95) | < 600 ms |
| NFR-03 | System availability | 99.9% uptime |
| NFR-04 | JWT signing algorithm | RS256 (asymmetric) |
| NFR-05 | Refresh token storage | `HttpOnly`, `Secure`, `SameSite=Strict` cookie |
| NFR-06 | Password reset / verification emails | Delivered within 30 seconds (p95) |
| NFR-07 | OWASP compliance | ASVS Level 2 for authentication controls |

### 3.6 Data Requirements

| Entity | Key Fields |
|--------|------------|
| `users` | `id` (UUID), `email` (unique), `password_hash`, `email_verified`, `locked_until`, `created_at` |
| `refresh_tokens` | `id`, `user_id` (FK), `token_hash`, `family_id`, `expires_at`, `revoked_at` |
| `email_verification_tokens` | `id`, `user_id` (FK), `token_hash`, `expires_at` |
| `password_reset_tokens` | `id`, `user_id` (FK), `token_hash`, `expires_at`, `used_at` |

### 3.7 Dependencies & Assumptions

- **Email service:** A transactional email provider (e.g., AWS SES or SendGrid) is available and configured before go-live.
- **Key management:** RS256 private/public key pairs are generated, stored securely (e.g., AWS Secrets Manager), and rotated quarterly.
- **HTTPS:** All endpoints are served exclusively over TLS in staging and production environments.
- **React 19 client:** Token refresh logic is handled client-side using a silent refresh strategy; the access token is stored in memory only (never `localStorage`).

### 3.8 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Credential stuffing attacks | High | High | Rate limiting + account lockout (FR-06) |
| Refresh token theft | Medium | High | Token rotation with reuse detection (FR-05) |
| Email delivery failure blocking registration | Medium | Medium | Retry queue + fallback provider |
| Reset link enumeration exposing registered emails | Low | Medium | Uniform HTTP 200 response regardless of email existence (FR-09) |

---

## 4. Auth Edge Cases — Enumeration & Acceptance Criteria

> **Addendum v1.1 — 2026-06-13**
> This section catalogues every meaningful edge case across the four named scenarios, assigns each a unique `EC-` identifier, and specifies Given/When/Then acceptance criteria. Each edge case also cross-references the FR it validates and notes the expected HTTP status code for fast triage during QA.

---

### 4.1 Duplicate Email

Scope: `POST /auth/register` — the email submitted already exists in the `users` table.

---

**EC-001 — Exact duplicate (same casing)**
*Validates: FR-01, FR-09 | Expected HTTP: 409*

- **Given** `alice@learnflow.io` is an existing, verified account in `users`
- **When** a new registration request is submitted with `email: "alice@learnflow.io"`
- **Then** the API returns HTTP 409 with body `{"detail": "An account with this email already exists"}`, no new `users` row is created, and no verification email is dispatched

---

**EC-002 — Duplicate email, different casing**
*Validates: FR-01 | Expected HTTP: 409*

- **Given** `alice@learnflow.io` is a registered account
- **When** a registration request is submitted with `email: "Alice@LearnFlow.IO"` (mixed case)
- **Then** the API normalises the email to lowercase before the uniqueness check, detects the collision, and returns HTTP 409 — confirming that email comparison is case-insensitive

---

**EC-003 — Duplicate email with leading/trailing whitespace**
*Validates: FR-01 | Expected HTTP: 409*

- **Given** `alice@learnflow.io` is a registered account
- **When** a registration request is submitted with `email: "  alice@learnflow.io  "` (padded whitespace)
- **Then** the API trims the value before the uniqueness check, detects the collision, and returns HTTP 409 — no new record is created

---

**EC-004 — Duplicate email belonging to an unverified account**
*Validates: FR-01, FR-02 | Expected HTTP: 409*

- **Given** `bob@learnflow.io` is registered but has `email_verified = false` (verification email not yet actioned)
- **When** a new registration request is submitted with `bob@learnflow.io`
- **Then** the API returns HTTP 409 and the response body includes a hint: `"A pending account exists for this email. Check your inbox or request a new verification link."` — the duplicate is rejected even for unverified accounts

---

**EC-005 — Duplicate email, password data not leaked in error**
*Validates: FR-09 | Expected HTTP: 409*

- **Given** any duplicate email scenario (EC-001 through EC-004)
- **When** the HTTP 409 response is rendered by the React 19 registration form
- **Then** the password and confirm-password fields are cleared, no submitted password value appears in the response body or server logs, and the email field is focused with the inline error — confirming zero credential leakage on collision

---

**EC-006 — Duplicate email submitted via direct API call (no UI)**
*Validates: FR-01 | Expected HTTP: 409*

- **Given** a client calls `POST /auth/register` directly with a duplicate email (bypassing the React form)
- **When** the FastAPI endpoint processes the request
- **Then** HTTP 409 is returned with the same structured error payload as EC-001 — confirming the guard lives at the API layer, not only in the UI

---

### 4.2 Weak Password

Scope: `POST /auth/register` and `POST /auth/password-reset/confirm` — the submitted password fails one or more complexity rules.

Complexity rules (from FR-01 / AC-001-03): minimum 8 characters · at least one uppercase letter · at least one digit · at least one special character.

---

**EC-007 — Password too short**
*Validates: FR-01, FR-10 | Expected HTTP: 422*

- **Given** a visitor is submitting the registration form
- **When** the password field contains `"Ab1!"` (4 characters — all rule types present but too short)
- **Then** the API returns HTTP 422 with `{"field": "password", "error": "Password must be at least 8 characters"}` and no `users` record is created

---

**EC-008 — Password missing uppercase letter**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits registration with `password: "abcdef1!"`
- **When** the API validates the password
- **Then** HTTP 422 is returned with `{"field": "password", "error": "Password must contain at least one uppercase letter"}` and registration is rejected

---

**EC-009 — Password missing digit**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits registration with `password: "Abcdefg!"`
- **When** the API validates the password
- **Then** HTTP 422 is returned with `{"field": "password", "error": "Password must contain at least one digit"}` and registration is rejected

---

**EC-010 — Password missing special character**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits registration with `password: "Abcdef12"`
- **When** the API validates the password
- **Then** HTTP 422 is returned with `{"field": "password", "error": "Password must contain at least one special character"}` and registration is rejected

---

**EC-011 — Multiple rules failed simultaneously**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits registration with `password: "abc"` (too short, no uppercase, no digit, no special character)
- **When** the API validates the password
- **Then** HTTP 422 is returned with an `errors` array containing one entry per violated rule — all violations are reported in a single response, not one at a time

---

**EC-012 — Password and confirm-password do not match**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits `password: "Secure1!"` and `confirm_password: "Secure2!"`
- **When** the API cross-validates the two fields
- **Then** HTTP 422 is returned with `{"field": "confirm_password", "error": "Passwords do not match"}` and no record is created

---

**EC-013 — Password is entirely whitespace**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits `password: "        "` (8 space characters — satisfies length but is trivially weak)
- **When** the API validates the password
- **Then** the API trims the value, detects it as empty after trimming, and returns HTTP 422 with `{"field": "password", "error": "Password cannot be blank or whitespace only"}`

---

**EC-014 — Weak password on password reset (not just registration)**
*Validates: FR-07 | Expected HTTP: 422*

- **Given** a user follows a valid password-reset link and submits `new_password: "password"` (common, no complexity)
- **When** `POST /auth/password-reset/confirm` validates the new password
- **Then** HTTP 422 is returned with the relevant failed rule(s) — confirming the same complexity rules apply at reset time, not only at registration

---

**EC-015 — New password same as current password on reset**
*Validates: FR-07 | Expected HTTP: 422*

- **Given** a user's current `password_hash` bcrypt-matches `"OldPass1!"`
- **When** they submit `new_password: "OldPass1!"` via a valid reset token
- **Then** HTTP 422 is returned with `{"field": "new_password", "error": "New password must differ from your current password"}` — the reset is rejected and the token remains valid for resubmission

---

**EC-016 — Password field empty on submission**
*Validates: FR-01 | Expected HTTP: 422*

- **Given** a visitor submits the registration form with an empty `password` field
- **When** the API receives the request
- **Then** HTTP 422 is returned before any bcrypt operation — confirming null/empty input is caught at the validation layer, not the hashing layer

---

### 4.3 Expired Token

Scope covers three token types: JWT access tokens, refresh tokens, and email verification tokens. Password-reset token expiry is covered in Section 4.4 (overlapping scenario) and cross-referenced here.

---

**EC-017 — Expired JWT access token on protected endpoint**
*Validates: FR-03, FR-04 | Expected HTTP: 401*

- **Given** a user holds a JWT access token whose `exp` claim is in the past by any amount
- **When** they call any protected FastAPI endpoint with `Authorization: Bearer <expired_token>`
- **Then** the `Depends(get_current_user)` guard raises HTTP 401 with `{"detail": "Token has expired"}` and the request is not processed

---

**EC-018 — Expired access token — client-side silent refresh succeeds**
*Validates: FR-04, FR-05 (NFR via AC-005-02) | Expected HTTP: 200 (after refresh)*

- **Given** the React 19 client detects the in-memory access token is expired (via `exp` claim check)
- **When** it calls `POST /auth/refresh` with the valid `HttpOnly` refresh cookie before retrying the original request
- **Then** a new access token is returned, the original request is retried with the new token, and the user sees no interruption or error

---

**EC-019 — Expired access token — no valid refresh token available**
*Validates: FR-04 | Expected HTTP: 401*

- **Given** the React 19 client detects the access token is expired and `POST /auth/refresh` returns HTTP 401 (refresh token also expired or absent)
- **When** the client handles the 401 from the refresh call
- **Then** the in-memory access token is cleared, the user is redirected to `/login`, and a non-alarming banner reads "Your session has expired. Please log in again."

---

**EC-020 — Expired refresh token presented directly to refresh endpoint**
*Validates: FR-04 | Expected HTTP: 401*

- **Given** a refresh token whose `expires_at` is in the past exists in `refresh_tokens`
- **When** `POST /auth/refresh` receives the corresponding `HttpOnly` cookie
- **Then** HTTP 401 is returned with `{"detail": "Session expired. Please log in again."}`, the expired row is deleted from `refresh_tokens`, and the cookie is cleared

---

**EC-021 — Tampered / structurally invalid JWT**
*Validates: FR-03 | Expected HTTP: 401*

- **Given** a request arrives with a JWT whose signature has been altered (e.g., last character changed)
- **When** the RS256 verification step runs
- **Then** HTTP 401 is returned with `{"detail": "Invalid token"}` — no claims from the tampered token are trusted or logged to application output

---

**EC-022 — JWT signed with an unrecognised key (algorithm confusion)**
*Validates: FR-03 | Expected HTTP: 401*

- **Given** a client presents a JWT signed with HS256 (symmetric) rather than the expected RS256 key
- **When** the FastAPI guard evaluates the token
- **Then** HTTP 401 is returned — confirming the guard explicitly rejects tokens signed with any algorithm other than RS256 (`algorithms=["RS256"]` is hardcoded in the verifier)

---

**EC-023 — Expired email verification token**
*Validates: FR-02 | Expected HTTP: 410*

- **Given** an email verification token was issued more than 24 hours ago
- **When** the user clicks the link (or submits `GET /auth/verify-email?token=<value>`)
- **Then** HTTP 410 is returned, the token row is deleted from `email_verification_tokens`, and the UI presents: "This verification link has expired. [Resend verification email]" — the account remains with `email_verified = false`

---

**EC-024 — Verification token already used (replay)**
*Validates: FR-02 | Expected HTTP: 410*

- **Given** a verification token that was already consumed (row deleted from `email_verification_tokens`)
- **When** the same link is clicked a second time
- **Then** the token lookup returns no row, HTTP 410 is returned with the same "link expired" message as EC-023 — a reused token is indistinguishable from an expired one, preventing state disclosure

---

**EC-025 — Expired password-reset token (cross-reference)**
*Validates: FR-07 | Expected HTTP: 410 — See also AC-011-01*

- **Given** a password-reset token older than 1 hour is submitted to `POST /auth/password-reset/confirm`
- **When** the API evaluates the token's `expires_at`
- **Then** HTTP 410 is returned, the token is deleted, and the UI displays: "This reset link has expired. [Request a new one]" — no change is made to `users.password_hash`

---

**EC-026 — Reset token used after password was already reset with it**
*Validates: FR-07 | Expected HTTP: 410*

- **Given** a password-reset token was already consumed (`used_at` is set and row deleted)
- **When** the same token URL is submitted again
- **Then** HTTP 410 is returned with the same expired-link message — a replayed reset token is treated identically to an expired one

---

### 4.4 Password Reset for a Non-Existent Account

Scope: `POST /auth/password-reset/request` — the submitted email does not match any row in `users`.

---

**EC-027 — Reset requested for unregistered email (primary anti-enumeration case)**
*Validates: FR-07, FR-09 | Expected HTTP: 200*

- **Given** `unknown@example.com` does not exist in the `users` table
- **When** `POST /auth/password-reset/request` is called with `{"email": "unknown@example.com"}`
- **Then** the API returns HTTP 200 with the identical response body used for a valid email: `{"message": "If an account exists for this email, a reset link has been sent"}` — no reset token is created, no email is sent, and the response is indistinguishable from the success case, preventing account enumeration

---

**EC-028 — Response timing is normalised for non-existent vs. existing email**
*Validates: FR-09 | Expected HTTP: 200*

- **Given** reset is requested for both a registered email and an unregistered email in separate calls
- **When** response times for both are measured across 100 samples
- **Then** the p95 response times differ by no more than 50 ms — confirming the API performs the same work (or an equivalent delay) regardless of email existence, preventing timing-based enumeration

---

**EC-029 — Reset requested for non-existent email, no DB side-effects**
*Validates: FR-07 | Expected HTTP: 200*

- **Given** `ghost@example.com` does not exist in `users`
- **When** the reset request is processed
- **Then** zero rows are inserted into `password_reset_tokens`, zero emails are dispatched, and the transactional email provider's send log shows no record for `ghost@example.com`

---

**EC-030 — Reset requested for soft-deleted / deactivated account**
*Validates: FR-07, FR-09 | Expected HTTP: 200*

- **Given** a `users` row exists for `deactivated@learnflow.io` with `status = 'deactivated'`
- **When** a reset is requested for that email
- **Then** the API treats the account as non-existent for reset purposes, returns HTTP 200 with the standard message, creates no token, and sends no email — a deactivated account cannot be reactivated via the password-reset flow

---

**EC-031 — Reset requested for email with SQL/script injection characters**
*Validates: FR-07, FR-09 | Expected HTTP: 422 or 200*

- **Given** a caller submits `email: "'; DROP TABLE users;--"` or similar malformed input
- **When** the FastAPI Pydantic model validates the field
- **Then** HTTP 422 is returned immediately with `{"field": "email", "error": "Invalid email format"}` — the value never reaches the database layer; ORM parameterisation provides a second line of defence even if validation were bypassed

---

**EC-032 — Multiple reset requests for the same non-existent email in rapid succession**
*Validates: FR-07, FR-09 | Expected HTTP: 200 (rate-limited after threshold)*

- **Given** `ghost@example.com` does not exist in `users`
- **When** 10 reset requests are submitted for that address within 60 seconds
- **Then** the first 5 return HTTP 200 (standard response), requests 6–10 return HTTP 429 `{"detail": "Too many requests. Please wait before trying again."}` — confirming that the rate limiter fires on the endpoint regardless of whether the account exists, and the limit itself does not confirm or deny account existence

---

### 4.5 Edge Case Coverage Matrix

| EC ID | Scenario | HTTP | FR Validated | Test Type |
|-------|----------|------|--------------|-----------|
| EC-001 | Exact duplicate email | 409 | FR-01, FR-09 | Integration |
| EC-002 | Duplicate — case-insensitive | 409 | FR-01 | Integration |
| EC-003 | Duplicate — trimmed whitespace | 409 | FR-01 | Integration |
| EC-004 | Duplicate — unverified account | 409 | FR-01, FR-02 | Integration |
| EC-005 | No credential leak on 409 | 409 | FR-09 | Security / E2E |
| EC-006 | Duplicate via direct API | 409 | FR-01 | Integration |
| EC-007 | Password too short | 422 | FR-01 | Unit |
| EC-008 | No uppercase | 422 | FR-01 | Unit |
| EC-009 | No digit | 422 | FR-01 | Unit |
| EC-010 | No special character | 422 | FR-01 | Unit |
| EC-011 | Multiple rules failed | 422 | FR-01 | Unit |
| EC-012 | Password / confirm mismatch | 422 | FR-01 | Unit |
| EC-013 | Whitespace-only password | 422 | FR-01 | Unit |
| EC-014 | Weak password on reset | 422 | FR-07 | Integration |
| EC-015 | New password same as current | 422 | FR-07 | Integration |
| EC-016 | Empty password field | 422 | FR-01 | Unit |
| EC-017 | Expired JWT on protected route | 401 | FR-03, FR-04 | Integration |
| EC-018 | Expired token — silent refresh succeeds | 200 | FR-04, FR-05 | E2E |
| EC-019 | Expired token — refresh also expired | 401 | FR-04 | E2E |
| EC-020 | Expired refresh token on refresh endpoint | 401 | FR-04 | Integration |
| EC-021 | Tampered JWT | 401 | FR-03 | Security |
| EC-022 | Algorithm confusion (HS256 → RS256) | 401 | FR-03 | Security |
| EC-023 | Expired email verification token | 410 | FR-02 | Integration |
| EC-024 | Verification token replay | 410 | FR-02 | Integration |
| EC-025 | Expired password-reset token | 410 | FR-07 | Integration |
| EC-026 | Reset token replay after use | 410 | FR-07 | Integration |
| EC-027 | Reset for unregistered email | 200 | FR-07, FR-09 | Integration |
| EC-028 | Timing normalisation — non-existent email | 200 | FR-09 | Security / Perf |
| EC-029 | No DB side-effects for non-existent email | 200 | FR-07 | Integration |
| EC-030 | Reset for deactivated account | 200 | FR-07, FR-09 | Integration |
| EC-031 | Injection characters in email | 422 | FR-07, FR-09 | Security |
| EC-032 | Rate limit on reset — non-existent email | 429 | FR-07, FR-09 | Integration |

---

*Addendum Owner: LearnFlow BA Team | Linked Epic: AUTH-001 | Status: Ready for Dev Review*
