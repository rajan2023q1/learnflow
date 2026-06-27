import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

export type ButtonProps = {
  children?: ReactNode;
  variant?: Variant;
  size?: Size;
  block?: boolean;
  loading?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  style?: CSSProperties;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'style'>;

/**
 * LearnFlow Button — primary action element.
 * Variants: primary (indigo), secondary (outline), ghost, danger.
 * Sizes: sm, md, lg, plus `block` for full-width (used on auth forms).
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  block = false,
  loading = false,
  disabled = false,
  iconLeft = null,
  iconRight = null,
  type = 'button',
  onClick,
  style = {},
  ...rest
}: ButtonProps) {
  const sizes: Record<Size, { height: number; padding: string; font: string; radius: string; gap: number }> = {
    sm: { height: 36, padding: '0 14px', font: 'var(--text-sm)', radius: 'var(--radius-sm)', gap: 6 },
    md: { height: 44, padding: '0 18px', font: 'var(--text-sm)', radius: 'var(--radius-md)', gap: 8 },
    lg: { height: 52, padding: '0 24px', font: 'var(--text-base)', radius: 'var(--radius-md)', gap: 8 },
  };
  const s = sizes[size] || sizes.md;

  const variants: Record<Variant, CSSProperties> = {
    primary: {
      background: 'var(--brand)',
      color: 'var(--on-brand)',
      border: '1px solid transparent',
      boxShadow: 'var(--shadow-xs)',
    },
    secondary: {
      background: 'var(--surface-card)',
      color: 'var(--text-strong)',
      border: '1px solid var(--border-strong)',
      boxShadow: 'var(--shadow-xs)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--brand)',
      border: '1px solid transparent',
    },
    danger: {
      background: 'var(--danger-600)',
      color: '#fff',
      border: '1px solid transparent',
      boxShadow: 'var(--shadow-xs)',
    },
  };

  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: s.gap,
        width: block ? '100%' : 'auto',
        height: s.height,
        padding: s.padding,
        fontSize: s.font,
        fontWeight: 'var(--weight-semibold)' as unknown as number,
        fontFamily: 'var(--font-sans)',
        letterSpacing: 'var(--tracking-tight)',
        borderRadius: s.radius,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        opacity: isDisabled ? 0.55 : 1,
        transition:
          'background var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard)',
        whiteSpace: 'nowrap',
        ...variants[variant],
        ...style,
      }}
      onMouseDown={(e) => {
        if (!isDisabled) e.currentTarget.style.transform = 'translateY(1px)';
      }}
      onMouseUp={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
      }}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden="true"
          style={{
            width: 15,
            height: 15,
            borderRadius: '50%',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            display: 'inline-block',
            animation: 'lf-spin 0.7s linear infinite',
          }}
        />
      )}
      {!loading && iconLeft}
      {children}
      {!loading && iconRight}
    </button>
  );
}
