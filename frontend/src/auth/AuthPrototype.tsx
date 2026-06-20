import { useRef, useState } from 'react';
import { Alert } from '../ds/Alert';
import type { AlertTone } from '../ds/Alert';
import { Button } from '../ds/Button';
import { Checkbox } from '../ds/Checkbox';
import { Input } from '../ds/Input';
import { Logo } from '../ds/Logo';
import { PasswordInput, scorePassword } from '../ds/PasswordInput';
import { ArrowLeftIcon, LockIcon, MailIcon, MailOpenIcon, SendIcon } from '../ds/icons';

type Screen = 'login' | 'register' | 'forgot' | 'verify' | 'sent';

type AlertState = { tone: AlertTone; title: string; msg: string } | null;

const validEmail = (x: string) => /\S+@\S+\.\S+/.test((x || '').trim());

const linkStyle: React.CSSProperties = {
  color: 'var(--brand)',
  fontWeight: 600,
  textDecoration: 'none',
};

/**
 * LearnFlow authentication flow — the implemented Auth Prototype.
 *
 * Self-contained client-side click-through across five screens (login,
 * register, email verification, forgot password, reset-link-sent) wired
 * to mock submit handlers that mirror the API response classes described
 * in docs/UC-1-requirements.md. Swap the setTimeout handlers for real
 * `fetch` calls to the FastAPI auth endpoints to go live.
 *
 * Demo shortcuts on the login form:
 *   • any email + any password           → success
 *   • password `wrong`                    → HTTP 401 "Invalid email or password."
 *   • email starting `locked@`            → HTTP 429 account lockout
 */
export function AuthPrototype() {
  const [screen, setScreen] = useState<Screen>('login');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [confirm, setConfirm] = useState('');
  const [emailErr, setEmailErr] = useState('');
  const [pwErr, setPwErr] = useState('');
  const [confirmErr, setConfirmErr] = useState('');
  const [loading, setLoading] = useState(false);
  const [remember, setRemember] = useState(true);
  const [alert, setAlert] = useState<AlertState>(null);
  const [sentTo, setSentTo] = useState('');

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const nav = (next: Screen) => {
    if (timer.current) clearTimeout(timer.current);
    setScreen(next);
    setPw('');
    setConfirm('');
    setEmailErr('');
    setPwErr('');
    setConfirmErr('');
    setLoading(false);
    setAlert(null);
  };

  const goLogin = (e?: React.MouseEvent) => {
    e?.preventDefault();
    nav('login');
  };
  const goRegister = (e?: React.MouseEvent) => {
    e?.preventDefault();
    nav('register');
  };
  const goForgot = (e?: React.MouseEvent) => {
    e?.preventDefault();
    nav('forgot');
  };

  const onLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let ee = '';
    let pe = '';
    if (!validEmail(email)) ee = 'Enter a valid email address.';
    if (!pw) pe = 'Enter your password.';
    if (ee || pe) {
      setEmailErr(ee);
      setPwErr(pe);
      return;
    }
    setEmailErr('');
    setPwErr('');
    setLoading(true);
    setAlert(null);
    timer.current = setTimeout(() => {
      const id = email.trim().toLowerCase();
      if (id.indexOf('locked@') === 0) {
        setLoading(false);
        setAlert({
          tone: 'warning',
          title: 'Account temporarily locked',
          msg: 'Too many failed attempts. Try again in 15 minutes.',
        });
      } else if (pw === 'wrong') {
        setLoading(false);
        setAlert({ tone: 'danger', title: '', msg: 'Invalid email or password.' });
      } else {
        setLoading(false);
        setAlert({ tone: 'success', title: 'Welcome back', msg: 'Logging you in — taking you to your dashboard…' });
      }
    }, 700);
  };

  const onRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let ee = '';
    let pe = '';
    let ce = '';
    if (!validEmail(email)) ee = 'Enter a valid email address.';
    if (scorePassword(pw) < 4) pe = 'Use 8+ characters with an uppercase letter, a number, and a symbol.';
    if (!confirm || confirm !== pw) ce = 'Passwords don’t match.';
    if (ee || pe || ce) {
      setEmailErr(ee);
      setPwErr(pe);
      setConfirmErr(ce);
      return;
    }
    setEmailErr('');
    setPwErr('');
    setConfirmErr('');
    setLoading(true);
    timer.current = setTimeout(() => {
      setLoading(false);
      setSentTo(email.trim());
      setScreen('verify');
      setPw('');
      setConfirm('');
    }, 800);
  };

  const onForgotSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validEmail(email)) {
      setEmailErr('Enter a valid email address.');
      return;
    }
    setEmailErr('');
    setLoading(true);
    timer.current = setTimeout(() => {
      setLoading(false);
      setSentTo(email.trim());
      setScreen('sent');
    }, 700);
  };

  const onResend = () => setAlert({ tone: 'info', title: '', msg: 'Verification email resent.' });

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: 'minmax(380px,1fr) minmax(480px,1.05fr)',
        fontFamily: 'Inter, system-ui, sans-serif',
        background: '#f8fafc',
      }}
    >
      {/* ===================== BRAND PANEL ===================== */}
      <aside
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(135deg,#4f46e5 0%,#6366f1 45%,#14b8a6 100%)',
          color: '#fff',
          padding: '48px 56px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: 460,
            height: 460,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.10)',
            top: -160,
            right: -120,
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: 320,
            height: 320,
            borderRadius: '50%',
            background: 'rgba(94,234,212,0.18)',
            bottom: -120,
            left: -80,
          }}
        />
        <div style={{ position: 'relative' }}>
          <Logo inverse height={30} />
        </div>
        <div style={{ position: 'relative', maxWidth: 430 }}>
          <h1 style={{ fontSize: 44, fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.1, margin: '0 0 16px' }}>
            Learn without limits.
          </h1>
          <p style={{ fontSize: 18, lineHeight: 1.65, color: 'rgba(255,255,255,0.86)', margin: 0 }}>
            Pick up in-demand skills at your own pace, track your progress, and earn certificates that move your career
            forward.
          </p>
        </div>
        <div style={{ position: 'relative', display: 'flex', gap: 18, fontSize: 14, color: 'rgba(255,255,255,0.82)' }}>
          <span>Self-paced courses</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span>Verified certificates</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span>Bank-grade security</span>
        </div>
      </aside>

      {/* ===================== FORM PANEL ===================== */}
      <main
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 24px',
          background: '#ffffff',
        }}
      >
        <div style={{ width: '100%', maxWidth: 440 }}>
          {/* shared alert */}
          {alert && (
            <div style={{ marginBottom: 20 }}>
              <Alert tone={alert.tone} title={alert.title || undefined} onClose={() => setAlert(null)}>
                {alert.msg}
              </Alert>
            </div>
          )}

          {/* ============ LOGIN ============ */}
          {screen === 'login' && (
            <form onSubmit={onLoginSubmit}>
              <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.01em', color: '#0f172a', margin: '0 0 8px' }}>
                Welcome to LearnFlow
              </h2>
              <p style={{ fontSize: 16, color: '#64748b', margin: '0 0 28px' }}>Log in to continue learning.</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <Input
                  label="Email address"
                  type="email"
                  placeholder="you@example.com"
                  iconLeft={<MailIcon />}
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setEmailErr('');
                  }}
                  error={emailErr}
                  required
                />
                <PasswordInput
                  label="Password"
                  iconLeft={<LockIcon />}
                  value={pw}
                  onChange={(e) => {
                    setPw(e.target.value);
                    setPwErr('');
                  }}
                  error={pwErr}
                  required
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Checkbox label="Remember me" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                  <a href="#" onClick={goForgot} style={{ ...linkStyle, fontSize: 14 }}>
                    Forgot password?
                  </a>
                </div>
                <Button block size="lg" type="submit" loading={loading}>
                  Log in
                </Button>
              </div>

              <p style={{ fontSize: 13, color: '#94a3b8', textAlign: 'center', margin: '14px 0 0', lineHeight: 1.5 }}>
                Demo: any email logs in · password{' '}
                <code style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#64748b' }}>wrong</code>{' '}
                triggers the error · an email starting{' '}
                <code style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#64748b' }}>locked@</code>{' '}
                triggers lockout
              </p>
              <p style={{ fontSize: 14, color: '#64748b', textAlign: 'center', marginTop: 18 }}>
                New to LearnFlow?{' '}
                <a href="#" onClick={goRegister} style={linkStyle}>
                  Create an account
                </a>
              </p>
            </form>
          )}

          {/* ============ REGISTER ============ */}
          {screen === 'register' && (
            <form onSubmit={onRegisterSubmit}>
              <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.01em', color: '#0f172a', margin: '0 0 8px' }}>
                Create your account
              </h2>
              <p style={{ fontSize: 16, color: '#64748b', margin: '0 0 28px' }}>Start learning today — it's free to begin.</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <Input
                  label="Email address"
                  type="email"
                  placeholder="you@example.com"
                  iconLeft={<MailIcon />}
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setEmailErr('');
                  }}
                  error={emailErr}
                  required
                />
                <PasswordInput
                  label="Password"
                  iconLeft={<LockIcon />}
                  value={pw}
                  onChange={(e) => {
                    setPw(e.target.value);
                    setPwErr('');
                  }}
                  error={pwErr}
                  showStrength
                  required
                />
                <PasswordInput
                  label="Confirm password"
                  iconLeft={<LockIcon />}
                  value={confirm}
                  onChange={(e) => {
                    setConfirm(e.target.value);
                    setConfirmErr('');
                  }}
                  error={confirmErr}
                  required
                />
                <Button block size="lg" type="submit" loading={loading}>
                  Create account
                </Button>
              </div>

              <p style={{ fontSize: 14, color: '#64748b', textAlign: 'center', marginTop: 24 }}>
                Already have an account?{' '}
                <a href="#" onClick={goLogin} style={linkStyle}>
                  Log in
                </a>
              </p>
            </form>
          )}

          {/* ============ FORGOT PASSWORD ============ */}
          {screen === 'forgot' && (
            <form onSubmit={onForgotSubmit}>
              <a
                href="#"
                onClick={goLogin}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  color: '#64748b',
                  fontSize: 14,
                  fontWeight: 600,
                  textDecoration: 'none',
                  marginBottom: 20,
                }}
              >
                <ArrowLeftIcon />
                Back to log in
              </a>
              <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.01em', color: '#0f172a', margin: '0 0 8px' }}>
                Reset your password
              </h2>
              <p style={{ fontSize: 16, color: '#64748b', margin: '0 0 28px' }}>
                Enter your email and we'll send you a link to set a new password.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <Input
                  label="Email address"
                  type="email"
                  placeholder="you@example.com"
                  iconLeft={<MailIcon />}
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setEmailErr('');
                  }}
                  error={emailErr}
                  required
                />
                <Button block size="lg" type="submit" loading={loading}>
                  Send reset link
                </Button>
              </div>
            </form>
          )}

          {/* ============ VERIFY (post-register confirmation) ============ */}
          {screen === 'verify' && (
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: '50%',
                  background: '#eef2ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 24px',
                }}
              >
                <MailOpenIcon />
              </div>
              <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.01em', color: '#0f172a', margin: '0 0 10px' }}>
                Check your inbox
              </h2>
              <p style={{ fontSize: 16, color: '#64748b', margin: '0 0 28px', lineHeight: 1.6 }}>
                We sent a verification link to <strong style={{ color: '#0f172a' }}>{sentTo}</strong>. Click it to activate
                your account, then log in.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Button block size="lg" variant="secondary" onClick={onResend}>
                  Resend verification email
                </Button>
                <a href="#" onClick={goLogin} style={{ ...linkStyle, fontSize: 14, padding: 8 }}>
                  Back to log in
                </a>
              </div>
            </div>
          )}

          {/* ============ RESET LINK SENT confirmation ============ */}
          {screen === 'sent' && (
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: '50%',
                  background: '#eef2ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 24px',
                }}
              >
                <SendIcon />
              </div>
              <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.01em', color: '#0f172a', margin: '0 0 10px' }}>
                Check your inbox
              </h2>
              <p style={{ fontSize: 16, color: '#64748b', margin: '0 0 28px', lineHeight: 1.6 }}>
                If an account exists for <strong style={{ color: '#0f172a' }}>{sentTo}</strong>, a password reset link is on
                its way. The link expires in 30 minutes.
              </p>
              <Button block size="lg" onClick={goLogin}>
                Back to log in
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
