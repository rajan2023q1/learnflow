import type { CSSProperties } from 'react';

/**
 * LearnFlow Logo — brand mark + wordmark. Inline SVG so it inherits crisp
 * rendering at any size and supports the inverse (on-dark) treatment.
 */
export function Logo({
  variant = 'full',
  inverse = false,
  height = 32,
  style = {},
}: {
  variant?: 'full' | 'mark';
  inverse?: boolean;
  height?: number;
  style?: CSSProperties;
}) {
  const markBlue = '#4F46E5';
  const wordDark = inverse ? '#FFFFFF' : '#0F172A';
  const wordAccent = inverse ? '#A5B4FC' : '#4F46E5';
  const topChevron = '#5EEAD4';
  const markBg = inverse ? 'rgba(255,255,255,0.12)' : markBlue;
  const chevron = '#FFFFFF';

  if (variant === 'mark') {
    const s = height;
    return (
      <svg width={s} height={s} viewBox="0 0 40 40" fill="none" style={style} role="img" aria-label="LearnFlow">
        <rect width="40" height="40" rx="10" fill={markBg} />
        <path d="M10 26 L20 17.5 L30 26" stroke={chevron} strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M10 18.5 L20 10 L30 18.5" stroke={topChevron} strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  const w = (156 / 36) * height;
  return (
    <svg width={w} height={height} viewBox="0 0 156 36" fill="none" style={style} role="img" aria-label="LearnFlow">
      <rect width="36" height="36" rx="9" fill={markBg} />
      <path d="M9 23.5 L18 16 L27 23.5" stroke={chevron} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 16.5 L18 9 L27 16.5" stroke={topChevron} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <text x="46" y="24.5" fontFamily="Inter, system-ui, sans-serif" fontSize="20" fontWeight="700" letterSpacing="-0.02em" fill={wordDark}>
        Learn<tspan fill={wordAccent}>Flow</tspan>
      </text>
    </svg>
  );
}
