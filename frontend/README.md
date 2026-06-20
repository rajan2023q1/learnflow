# LearnFlow — Auth frontend

A React 19 + Vite + TypeScript implementation of the LearnFlow **Auth Prototype**
(`Auth Prototype.dc.html` from the Claude Design project), built on the LearnFlow
design system tokens and components.

## What's here

A self-contained, client-side auth click-through across five screens:

| Screen | Trigger |
|--------|---------|
| **Login** | default |
| **Register** | "Create an account" |
| **Email verification** | successful register |
| **Forgot password** | "Forgot password?" |
| **Reset link sent** | submit forgot-password |

### Demo shortcuts (login form)

- any email + any password → success banner
- password `wrong` → `401 Invalid email or password.`
- email starting `locked@` → `429` account lockout warning

These mirror the API response classes in [`../docs/UC-1-requirements.md`](../docs/UC-1-requirements.md).

## Run

```bash
npm install
npm run dev      # http://localhost:5173
```

Other scripts: `npm run build`, `npm run preview`, `npm run typecheck`.

## Structure

```
src/
  ds/                 design-system components (ported from the DS project)
    Button, Input, PasswordInput, Checkbox, Alert, Logo, icons
  auth/
    AuthPrototype.tsx  the five-screen auth flow + mock handlers
  styles/
    tokens/            colors · typography · spacing · fonts (verbatim DS tokens)
    global.css
```

## Going live

The submit handlers in `AuthPrototype.tsx` use `setTimeout` to simulate the
backend. Replace each with a `fetch` to the FastAPI auth endpoints
(`POST /auth/login`, `/auth/register`, `/auth/password-reset/request`, …) and
keep the access token in memory only per the requirements (never `localStorage`).
