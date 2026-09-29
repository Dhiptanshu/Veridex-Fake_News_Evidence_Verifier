import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-line bg-surface shadow-card ${className}`}>{children}</section>;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{children}</p>;
}

export function PlaceholderTag() {
  return (
    <span className="rounded-full border border-neutral/40 bg-neutral/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral">
      placeholder
    </span>
  );
}
