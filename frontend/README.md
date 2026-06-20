# LearnFlow — Auth frontend

A React 19 + Vite + TypeScript implementation of the LearnFlow **Auth Prototype**
(`Auth Prototype.dc.html` from the Claude Design project), built on the LearnFlow
design system tokens and components.

## What's here

An auth click-through across five screens, wired to the FastAPI backend:

| Screen | Trigger | Endpoint |
|--------|---------|----------|
| **Login** | default | `POST /auth/login` |
| **Register** | "Create an account" | `POST /auth/register` |
| **Email verification** | successful register | `POST /auth/verify-email/resend` (resend) |
| **Forgot password** | "Forgot password?" | `POST /auth/password-reset/request` |
| **Reset link sent** | submit forgot-password | — |

Server responses map to the UI per [`../docs/UC-1-requirements.md`](../docs/UC-1-requirements.md):
`401` → "Invalid email or password.", `403` → jump to the verify screen,
`429` → lockout warning, `409` → inline email error on register.

The access token is held **in memory only** (never `localStorage`); the refresh
token rides in an HttpOnly cookie, so requests use `credentials: 'include'`.

## Run

Start the [backend](../backend) first (`uvicorn app.main:app` on `:8000`), then:

```bash
npm install
cp .env.example .env   # optional — sets VITE_API_BASE_URL (default :8000)
npm run dev            # http://localhost:5173
```

Other scripts: `npm run build`, `npm run preview`, `npm run typecheck`.

## Structure

```
src/
  api/
    auth.ts            typed fetch client + in-memory access-token store
  ds/                  design-system components (ported from the DS project)
    Button, Input, PasswordInput, Checkbox, Alert, Logo, icons
  auth/
    AuthPrototype.tsx  the five-screen auth flow, wired to api/auth
  styles/
    tokens/            colors · typography · spacing · fonts (verbatim DS tokens)
    global.css
```

## Not yet wired

Email verification and password reset are completed from links in the email
(console output in the dev backend). The corresponding landing pages
(`/verify-email?token=…`, `/reset-password?token=…`) aren't built — the prototype
has no router — but `authApi.verifyEmail` / `authApi.confirmPasswordReset` are
ready in `api/auth.ts` for when they are. Silent token refresh (AC-005-02) can be
layered on with `authApi.refresh()`.
