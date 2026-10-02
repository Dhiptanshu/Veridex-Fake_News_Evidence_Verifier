import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Label } from "@/api/types";

/** Shared primitives: soft cards, pill badges, gradient primary buttons. */

export function Panel({
  title, actions, children, className = "", flush = false, subtitle,
}: { title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; flush?: boolean }) {
  return (
    <section className={`rounded-2xl border border-line bg-surface shadow-card ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-5 pb-0 pt-4">
          <div className="min-w-0">
            <h3 className="text-[13px] font-semibold tracking-tight">{title}</h3>
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        </header>
      )}
      <div className={flush ? "pt-3" : "p-5 pt-3"}>{children}</div>
    </section>
  );
}

type Tone = "neutral" | "supported" | "refuted" | "accent" | "warn";
const TONES: Record<Tone, string> = {
  neutral: "bg-surface2 text-muted",
  supported: "bg-supported/12 text-supported",
  refuted: "bg-refuted/12 text-refuted",
  accent: "bg-accent/12 text-accent",
  warn: "bg-warn/14 text-warn",
};

export function Badge({ tone = "neutral", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium leading-4 ${TONES[tone]} ${className}`}>{children}</span>;
}

export const LABEL_TONE: Record<Label, Tone> = { supported: "supported", refuted: "refuted", not_enough_info: "neutral" };
export const LABEL_TEXT: Record<Label, string> = { supported: "Supported", refuted: "Refuted", not_enough_info: "Not enough info" };
export const LABEL_COLOR: Record<Label, string> = { supported: "var(--supported)", refuted: "var(--refuted)", not_enough_info: "var(--neutral)" };

export function VerdictBadge({ label, className = "" }: { label: Label; className?: string }) {
  return <Badge tone={LABEL_TONE[label]} className={className}>{LABEL_TEXT[label]}</Badge>;
}

export function Button({
  variant = "secondary", size = "md", icon, loading, children, className = "", ...rest
}: { variant?: "primary" | "secondary" | "ghost"; size?: "sm" | "md"; icon?: ReactNode; loading?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const v = {
    primary: "bg-brand text-accentink shadow-brand hover:brightness-110 active:brightness-95",
    secondary: "border border-line bg-surface hover:bg-surface2",
    ghost: "text-muted hover:bg-surface2 hover:text-ink",
  }[variant];
  const sz = size === "sm" ? "h-8 px-3 text-xs" : "h-10 px-4 text-[13px]";
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={`inline-flex shrink-0 items-center justify-center gap-1.5 rounded-xl font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${sz} ${v} ${className}`}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}

export function Segmented<T extends string>({
  value, onChange, options, ariaLabel,
}: { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; ariaLabel?: string }) {
  return (
    <div role="group" aria-label={ariaLabel} className="inline-flex rounded-xl bg-surface2 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${value === o.value ? "bg-surface text-ink shadow-card" : "text-muted hover:text-ink"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Pill-style tabs. */
export function Tabs<T extends string>({
  value, onChange, tabs,
}: { value: T; onChange: (v: T) => void; tabs: { value: T; label: ReactNode; count?: number }[] }) {
  return (
    <div role="tablist" className="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl bg-surface2 p-1">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={`shrink-0 rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition ${value === t.value ? "bg-surface text-ink shadow-card" : "text-muted hover:text-ink"}`}
        >
          {t.label}
          {t.count !== undefined && <span className="ml-1.5 rounded-full bg-accent/12 px-1.5 text-[11px] text-accent">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-mono text-2xl font-medium tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function Empty({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      {icon && <div className="grid size-12 place-items-center rounded-2xl bg-accent/10 text-accent">{icon}</div>}
      <p className="text-sm font-semibold">{title}</p>
      {children && <p className="max-w-md text-[13px] text-muted">{children}</p>}
      {action}
    </div>
  );
}

export function Select({
  value, onChange, children, ariaLabel, className = "",
}: { value: string; onChange: (v: string) => void; children: ReactNode; ariaLabel?: string; className?: string }) {
  return (
    <select
      value={value}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.value)}
      className={`h-9 rounded-xl border border-line bg-surface px-2.5 text-[13px] outline-none hover:bg-surface2 focus:border-accent ${className}`}
    >
      {children}
    </select>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="rounded-md border border-line bg-surface2 px-1.5 py-0.5 font-mono text-[10px] text-muted">{children}</kbd>;
}

export function ProbBar({ values, className = "" }: { values: { label: Label; value: number }[]; className?: string }) {
  return (
    <div className={`flex h-2 overflow-hidden rounded-full bg-surface2 ${className}`} role="img"
      aria-label={values.map((v) => `${LABEL_TEXT[v.label]} ${Math.round(v.value * 100)}%`).join(", ")}>
      {values.map((v) => <span key={v.label} style={{ width: `${v.value * 100}%`, background: LABEL_COLOR[v.label] }} />)}
    </div>
  );
}

/** Circular confidence gauge. */
export function Ring({ value, color, size = 96, stroke = 9, children }: { value: number; color: string; size?: number; stroke?: number; children?: ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(0, Math.min(1, value)))}
          style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(.2,.8,.2,1)" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">{children}</div>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

/** A coloured initial for a source (no third-party favicon requests, so which sites you check is never leaked). */
export function SourceMark({ url, name, size = 22 }: { url?: string | null; name: string; size?: number }) {
  let host = "";
  try { host = url ? new URL(url).hostname : ""; } catch { /* not a URL */ }
  const key = host || name;
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) % 360;
  const initial = (name || host || "?").replace(/^[^A-Za-z0-9]+/, "").charAt(0).toUpperCase() || "?";
  return (
    <span
      className="inline-grid shrink-0 place-items-center rounded-lg text-[11px] font-bold"
      style={{ width: size, height: size, background: `hsl(${h} 70% 55% / 0.16)`, color: `hsl(${h} 60% 45%)` }}
    >
      {initial}
    </span>
  );
}
