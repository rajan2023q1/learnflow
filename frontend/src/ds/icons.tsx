import type { ReactNode } from 'react';

/**
 * LearnFlow auth glyphs. Lucide-style: 1.5–2px stroke, no fill, currentColor.
 * Default field-icon size is 18px to sit neatly inside the 44px Input.
 */

type IconProps = {
  size?: number;
};

function Svg({ size = 18, children }: { size?: number; children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function MailIcon({ size = 18 }: IconProps) {
  return (
    <Svg size={size}>
      <rect x={2} y={4} width={20} height={16} rx={2} />
      <path d="m22 7-10 5L2 7" />
    </Svg>
  );
}

export function LockIcon({ size = 18 }: IconProps) {
  return (
    <Svg size={size}>
      <rect x={3} y={11} width={18} height={11} rx={2} />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </Svg>
  );
}

export function ArrowLeftIcon({ size = 16 }: IconProps) {
  return (
    <Svg size={size}>
      <path d="m12 19-7-7 7-7" />
      <path d="M19 12H5" />
    </Svg>
  );
}

/** Large open-envelope mark for the "Check your inbox" verification screen. */
export function MailOpenIcon({ size = 32 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--brand)"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x={2} y={4} width={20} height={16} rx={2} />
      <path d="m22 7-10 5L2 7" />
    </svg>
  );
}

/** Large paper-plane mark for the "reset link sent" screen. */
export function SendIcon({ size = 32 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--brand)"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4Z" />
    </svg>
  );
}
