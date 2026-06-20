import type { CSSProperties, ReactNode } from 'react';

export type AlertTone = 'success' | 'danger' | 'warning' | 'info';

export type AlertProps = {
  tone?: AlertTone;
  title?: string;
  children?: ReactNode;
  icon?: ReactNode;
  onClose?: () => void;
  style?: CSSProperties;
};

/**
 * LearnFlow inline Alert / banner for form-level feedback.
 * Tones map to the API response classes in the auth flows
 * (success, error, warning, info).
 */
export function Alert({ tone = 'info', title, children, icon, onClose, style = {} }: AlertProps) {
  const tones: Record<AlertTone, { bg: string; border: string; fg: string; dot: string }> = {
    success: { bg: 'var(--success-bg)', border: 'var(--success-border)', fg: 'var(--success-700)', dot: 'var(--success-600)' },
    danger: { bg: 'var(--danger-bg)', border: 'var(--danger-border)', fg: 'var(--danger-700)', dot: 'var(--danger-600)' },
    warning: { bg: 'var(--warning-bg)', border: 'var(--warning-border)', fg: 'var(--warning-700)', dot: 'var(--warning-600)' },
    info: { bg: 'var(--info-bg)', border: 'var(--info-border)', fg: 'var(--info-700)', dot: 'var(--info-600)' },
  };
  const t = tones[tone] || tones.info;

  const defaultIcons: Record<AlertTone, string> = {
    success: 'M5 10.5 L8.5 14 L15 6',
    danger: 'M10 6 V11 M10 14 h0.01',
    warning: 'M10 6 V11 M10 14 h0.01',
    info: 'M10 9 V14 M10 6 h0.01',
  };

  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '12px 14px',
        background: t.bg,
        border: `1px solid ${t.border}`,
        borderRadius: 'var(--radius-md)',
        ...style,
      }}
    >
      <span
        style={{
          flexShrink: 0,
          width: 20,
          height: 20,
          borderRadius: '50%',
          background: t.dot,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginTop: 1,
        }}
      >
        {icon || (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d={defaultIcons[tone] || defaultIcons.info} stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        {title && (
          <div
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--text-sm)',
              fontWeight: 'var(--weight-semibold)' as unknown as number,
              color: t.fg,
              marginBottom: children ? 2 : 0,
            }}
          >
            {title}
          </div>
        )}
        {children && (
          <div
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--text-sm)',
              color: t.fg,
              lineHeight: 'var(--leading-normal)',
            }}
          >
            {children}
          </div>
        )}
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss"
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: t.fg, padding: 2, lineHeight: 0, flexShrink: 0 }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 4 L12 12 M12 4 L4 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>
      )}
    </div>
  );
}
