import type { CSSProperties, ReactNode } from 'react';

export type CheckboxProps = {
  checked?: boolean;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  label?: ReactNode;
  disabled?: boolean;
  id?: string;
  style?: CSSProperties;
};

/**
 * LearnFlow Checkbox with adjacent label. Used for "Remember me", terms acceptance, etc.
 */
export function Checkbox({ checked = false, onChange, label, disabled = false, id, style = {} }: CheckboxProps) {
  const cbId = id || (typeof label === 'string' ? `lf-cb-${label.replace(/\s+/g, '-').toLowerCase()}` : undefined);
  return (
    <label
      htmlFor={cbId}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 10,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.55 : 1,
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-sm)',
        color: 'var(--text-body)',
        userSelect: 'none',
        ...style,
      }}
    >
      <span
        style={{
          width: 18,
          height: 18,
          flexShrink: 0,
          borderRadius: 'var(--radius-xs)',
          border: `1.5px solid ${checked ? 'var(--brand)' : 'var(--field-border)'}`,
          background: checked ? 'var(--brand)' : 'var(--field-bg)',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition:
            'background var(--duration-fast) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)',
        }}
      >
        {checked && (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M2.5 6.2 L5 8.6 L9.5 3.5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
      <input
        id={cbId}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }}
      />
      {label && <span>{label}</span>}
    </label>
  );
}
