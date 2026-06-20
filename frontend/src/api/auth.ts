/**
 * Typed client for the LearnFlow auth API (FastAPI, see ../../backend).
 *
 * - The access token is held in memory only (never localStorage) per the
 *   UC-1 requirement; the refresh token lives in an HttpOnly cookie, so every
 *   request uses `credentials: 'include'`.
 * - Errors are normalised to `ApiError` with the HTTP status and, for 422
 *   validation responses, a per-field message map.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/+$/, '');

let accessToken: string | null = null;
export function getAccessToken(): string | null {
  return accessToken;
}
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

// --- Silent refresh scheduling (AC-005-02) ---------------------------------
let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let onRefreshFailure: (() => void) | null = null;

/** Register a callback invoked when a silent refresh fails (session ended). */
export function setOnRefreshFailure(cb: (() => void) | null): void {
  onRefreshFailure = cb;
}

/** Schedule a silent token refresh ~1 min before the access token expires. */
export function scheduleRefresh(expiresInSeconds: number): void {
  stopRefresh();
  const delayMs = Math.max(expiresInSeconds - 60, 5) * 1000;
  refreshTimer = setTimeout(async () => {
    try {
      const result = await authApi.refresh();
      setAccessToken(result.access_token);
      scheduleRefresh(result.expires_in);
    } catch {
      setAccessToken(null);
      onRefreshFailure?.();
    }
  }, delayMs);
}

export function stopRefresh(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;
  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

type JsonBody = Record<string, unknown>;

interface FastApiValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

function toApiError(status: number, data: unknown): ApiError {
  const detail = (data as { detail?: unknown } | null)?.detail;

  // FastAPI 422 — array of {loc, msg}; map each to its field.
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    let first = '';
    for (const item of detail as FastApiValidationItem[]) {
      const loc = item.loc ?? [];
      const field = loc.length ? String(loc[loc.length - 1]) : '';
      const msg = String(item.msg ?? '').replace(/^Value error,\s*/, '');
      if (field && !fieldErrors[field]) fieldErrors[field] = msg;
      if (!first) first = msg;
    }
    return new ApiError(status, first || 'Please check the form and try again.', fieldErrors);
  }

  if (typeof detail === 'string') return new ApiError(status, detail);
  return new ApiError(status, 'Something went wrong. Please try again.');
}

async function request<T>(path: string, body?: JsonBody, method = 'POST'): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Is the API running on :8000?');
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw toApiError(res.status, data);
  return data as T;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface MessageResult {
  message: string;
}

export interface RegisterResult {
  message: string;
  /** True when the account was auto-verified (dev, no email provider). */
  email_verified: boolean;
}

export interface UserResult {
  id: string;
  email: string;
  email_verified: boolean;
  roles: string[];
  created_at: string;
}

export const authApi = {
  register: (email: string, password: string, confirmPassword: string) =>
    request<RegisterResult>('/auth/register', { email, password, confirm_password: confirmPassword }),

  verifyEmail: (token: string) => request<MessageResult>('/auth/verify-email', { token }),

  resendVerification: (email: string) =>
    request<MessageResult>('/auth/verify-email/resend', { email }),

  login: (email: string, password: string, remember = true) =>
    request<LoginResult>('/auth/login', { email, password, remember }),

  refresh: () => request<LoginResult>('/auth/refresh', {}),

  logout: () => request<MessageResult>('/auth/logout', {}),

  requestPasswordReset: (email: string) =>
    request<MessageResult>('/auth/password-reset/request', { email }),

  confirmPasswordReset: (token: string, password: string, confirmPassword: string) =>
    request<MessageResult>('/auth/password-reset/confirm', {
      token,
      password,
      confirm_password: confirmPassword,
    }),

  me: () => request<UserResult>('/auth/me', undefined, 'GET'),
};
