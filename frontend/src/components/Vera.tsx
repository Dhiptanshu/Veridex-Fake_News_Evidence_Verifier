/** Vera, the Veridex assistant: a friendly investigative journalist in round glasses with a magnifying glass. */
export function VeraAvatar({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" role="img" aria-label="Vera" className={`shrink-0 ${className}`}>
      <defs>
        <linearGradient id="vera-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7aa2ff" />
          <stop offset="1" stopColor="#2f5ce6" />
        </linearGradient>
        <clipPath id="vera-clip"><circle cx="20" cy="20" r="20" /></clipPath>
      </defs>
      <circle cx="20" cy="20" r="20" fill="url(#vera-bg)" />
      <g clipPath="url(#vera-clip)">
        {/* shoulders and a little press collar */}
        <path d="M5 42c0-8 6-12 15-12s15 4 15 12z" fill="#f4f7ff" />
        <path d="M15 30.5l5 4.5 5-4.5" fill="none" stroke="#2f5ce6" strokeWidth="1.6" strokeLinejoin="round" />
        {/* bob haircut behind the face */}
        <rect x="8.2" y="14" width="23.6" height="17" rx="9" fill="#14224f" />
        {/* face */}
        <circle cx="20" cy="21.5" r="9.4" fill="#ffe1cd" />
        {/* fringe */}
        <path d="M10.4 20.5C10.4 13.6 14.6 11 20 11s9.6 2.6 9.6 9.5c-2.4-4.2-5.6-5.6-9.6-5.6s-7.2 1.4-9.6 5.6z" fill="#14224f" />
        {/* round glasses */}
        <g fill="none" stroke="#14224f" strokeWidth="1.1">
          <circle cx="15.9" cy="22.2" r="3.3" />
          <circle cx="24.1" cy="22.2" r="3.3" />
          <path d="M19.2 22.1h1.6" />
        </g>
        <circle cx="15.9" cy="22.4" r="1.15" fill="#14224f" />
        <circle cx="24.1" cy="22.4" r="1.15" fill="#14224f" />
        <circle cx="16.3" cy="22" r="0.4" fill="#fff" />
        <circle cx="24.5" cy="22" r="0.4" fill="#fff" />
        {/* blush and smile */}
        <circle cx="13" cy="26.3" r="1.5" fill="#ff9db0" opacity="0.55" />
        <circle cx="27" cy="26.3" r="1.5" fill="#ff9db0" opacity="0.55" />
        <path d="M17.6 26.6q2.4 2.2 4.8 0" fill="none" stroke="#14224f" strokeWidth="1.2" strokeLinecap="round" />
      </g>
      {/* magnifying glass */}
      <g>
        <line x1="32.3" y1="32.3" x2="36.6" y2="36.6" stroke="#0e2a78" strokeWidth="2.6" strokeLinecap="round" />
        <circle cx="29.2" cy="29.2" r="4.6" fill="#ffffff" fillOpacity="0.55" stroke="#0e2a78" strokeWidth="2" />
      </g>
    </svg>
  );
}
