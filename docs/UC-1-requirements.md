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

*Document Owner: LearnFlow Product Team | Next Review: Sprint Planning — Auth Epic Kickoff*

