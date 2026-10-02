import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`card rounded-[22px] ${className}`}>{children}</section>;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-[12px] font-semibold uppercase tracking-wide text-muted">{children}</p>;
}

export function PlaceholderTag() {
  return (
    <span className="rounded-full bg-warn/16 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-warn">
      placeholder
    </span>
  );
}
