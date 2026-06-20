import { useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { Input } from './Input';

/** Evaluate password against LearnFlow complexity rules (≥8, upper, digit, special). */
export function scorePassword(pw = ''): number {
  const checks = [
    pw.length >= 8,
    /[A-Z]/.test(pw),
    /[0-9]/.test(pw),
    /[!@#$%^&*(),.?":{}|<>_\-[\]\\/+=;'`~]/.test(pw),
  ];
  return checks.filter(Boolean).length; // 0..4
}

export type PasswordInputProps = {
  label?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  error?: string;
  helper?: string;
  showStrength?: boolean;
  iconLeft?: ReactNode;
  required?: boolean;
  style?: CSSProperties;
};

/**
 * Password field with show/hide reveal toggle and optional strength meter.
 * Strength reflects the LearnFlow registration complexity rules.
 */
export function PasswordInput({
  label = 'Password',
  value = '',
  onChange,
  placeholder = '••••••••',
  error,
  helper,
  showStrength = false,
  iconLeft = null,
  required = false,
  style = {},
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const score = scorePassword(value);
  const labels = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['var(--danger-500)', 'var(--danger-500)', 'var(--warning-500)', 'var(--teal-500)', 'var(--success-600)'];

  const toggle = (
    <button
      type="button"
      onClick={() => setVisible((v) => !v)}
      aria-label={visible ? 'Hide password' : 'Show password'}
      style={{
        border: 'none',
        background: 'transparent',
        cursor: 'pointer',
        padding: 2,
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-xs)',
        fontWeight: 'var(--weight-medium)' as unknown as number,
        color: 'var(--text-muted)',
      }}
    >
      {visible ? 'Hide' : 'Show'}
    </button>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', ...style }}>
      <Input
        label={label}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        error={error}
        helper={helper}
        iconLeft={iconLeft}
        required={required}
        rightSlot={toggle}
      />
      {showStrength && value.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                style={{
                  flex: 1,
                  height: 4,
                  borderRadius: 'var(--radius-full)',
                  background: i < score ? colors[score] : 'var(--slate-200)',
                  transition: 'background var(--duration-normal) var(--ease-standard)',
                }}
              />
            ))}
          </div>
          <span
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--text-xs)',
              color: colors[score],
              fontWeight: 'var(--weight-medium)' as unknown as number,
            }}
          >
            {labels[score]}
          </span>
        </div>
      )}
    </div>
  );
}
