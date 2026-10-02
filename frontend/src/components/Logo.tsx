/** Veridex mark: a newspaper under a magnifying glass with a checkmark in the lens. Same artwork as public/favicon.svg. */
export function Logo({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="Veridex" className={className}>
      <defs>
        <linearGradient id="evlg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6c9bff" />
          <stop offset="1" stopColor="#2a52d9" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="17" fill="url(#evlg)" />
      <rect x="11" y="12" width="31" height="38" rx="4.5" fill="#f4f7ff" />
      <rect x="16" y="18" width="13" height="9" rx="1.8" fill="#2a52d9" />
      <rect x="32" y="18" width="6" height="2.6" rx="1.3" fill="#9db5f5" />
      <rect x="32" y="23.4" width="6" height="2.6" rx="1.3" fill="#9db5f5" />
      <rect x="16" y="31" width="22" height="2.6" rx="1.3" fill="#9db5f5" />
      <rect x="16" y="36" width="22" height="2.6" rx="1.3" fill="#9db5f5" />
      <rect x="16" y="41" width="12" height="2.6" rx="1.3" fill="#9db5f5" />
      <line x1="50" y1="48.5" x2="57" y2="55.5" stroke="#0e2a78" strokeWidth="6" strokeLinecap="round" />
      <circle cx="42" cy="40" r="11.5" fill="#ffffff" stroke="#0e2a78" strokeWidth="4.5" />
      <path d="M36.6 40.4l4 4 7-8.2" fill="none" stroke="#0fa86d" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
