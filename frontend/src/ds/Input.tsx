import { useState } from 'react';
import type { CSSProperties, InputHTMLAttributes, ReactNode } from 'react';

export type InputProps = {
  label?: string;
  error?: string;
  helper?: string;
  iconLeft?: ReactNode;
  rightSlot?: ReactNode;
  style?: CSSProperties;
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'style'>;

/**
 * LearnFlow text Input with label, helper/error text, and optional leading icon.
 * Used throughout auth forms (email, name) and settings.
 */
export function Input({
  label,
  id,
  type = 'text',
  value,
  onChange,
  placeholder,
  error,
  helper,
  iconLeft = null,
  disabled = false,
  required = false,
  rightSlot = null,
  style = {},
  ...rest
}: InputProps) {
  const [focused, setFocused] = useState(false);
  const inputId = id || (label ? `lf-${label.replace(/\s+/g, '-').toLowerCase()}` : undefined);
  const invalid = Boolean(error);

  const borderColor = invalid
    ? 'var(--danger-500)'
    : focused
      ? 'var(--border-focus)'
      : 'var(--field-border)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%', ...style }}>
      {label && (
        <label
          htmlFor={inputId}
          style={{
            color: 'var(--text-strong)',
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-sm)',
            fontWeight: 'var(--weight-medium)' as unknown as number,
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--danger-500)', marginLeft: 3 }}>*</span>}
        </label>
      )}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          height: 44,
          padding: '0 12px',
          background: disabled ? 'var(--field-disabled)' : 'var(--field-bg)',
          border: `1px solid ${borderColor}`,
          borderRadius: 'var(--radius-md)',
          boxShadow: focused && !invalid ? 'var(--shadow-focus)' : 'none',
          transition:
            'border-color var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard)',
        }}
      >
        {iconLeft && (
          <span style={{ display: 'inline-flex', color: 'var(--text-subtle)', flexShrink: 0 }}>{iconLeft}</span>
        )}
        <input
          id={inputId}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          aria-invalid={invalid}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            flex: 1,
            minWidth: 0,
            border: 'none',
            outline: 'none',
            background: 'transparent',
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-base)',
            color: 'var(--text-strong)',
          }}
          {...rest}
        />
        {rightSlot && <span style={{ display: 'inline-flex', flexShrink: 0 }}>{rightSlot}</span>}
      </div>
      {(error || helper) && (
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-xs)',
            color: invalid ? 'var(--danger-600)' : 'var(--text-muted)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          {error || helper}
        </span>
      )}
    </div>
  );
}
