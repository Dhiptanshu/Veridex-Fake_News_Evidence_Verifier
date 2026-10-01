import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Label } from "@/api/types";

/** Small shared primitives so every page has the same dense, quiet look. */

export function Panel({
  title, actions, children, className = "", flush = false,
}: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; flush?: boolean }) {
  return (
    <section className={`rounded-lg border border-line bg-surface ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
          <h3 className="text-[13px] font-semibold tracking-tight">{title}</h3>
          <div className="flex items-center gap-2">{actions}</div>
        </header>
      )}
      <div className={flush ? "" : "p-4"}>{children}</div>
    </section>
  );
}

type Tone = "neutral" | "supported" | "refuted" | "accent" | "warn";
const TONES: Record<Tone, string> = {
  neutral: "border-line bg-surface2 text-muted",
  supported: "border-supported/30 bg-supported/10 text-supported",
  refuted: "border-refuted/30 bg-refuted/10 text-refuted",
  accent: "border-accent/30 bg-accent/10 text-accent",
  warn: "border-warn/30 bg-warn/10 text-warn",
};

export function Badge({ tone = "neutral", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-4 ${TONES[tone]} ${className}`}>{children}</span>;
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
    primary: "bg-accent text-accentink hover:brightness-110",
    secondary: "border border-line bg-surface hover:bg-surface2",
    ghost: "text-muted hover:bg-surface2 hover:text-ink",
  }[variant];
  const sz = size === "sm" ? "h-7 px-2.5 text-xs" : "h-8 px-3 text-[13px]";
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={`inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${sz} ${v} ${className}`}
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
    <div role="group" aria-label={ariaLabel} className="inline-flex rounded-md border border-line bg-surface2 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={`rounded px-2.5 py-1 text-xs font-medium transition ${value === o.value ? "bg-surface text-ink shadow-card" : "text-muted hover:text-ink"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Tabs<T extends string>({
  value, onChange, tabs,
}: { value: T; onChange: (v: T) => void; tabs: { value: T; label: ReactNode; count?: number }[] }) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-line">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={`-mb-px border-b-2 px-3 py-2 text-[13px] font-medium transition ${value === t.value ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"}`}
        >
          {t.label}
          {t.count !== undefined && <span className="ml-1.5 rounded bg-surface2 px-1.5 text-[11px] text-muted">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-0.5 font-mono text-xl font-medium tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function Empty({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      {icon && <div className="grid size-10 place-items-center rounded-lg border border-line bg-surface2 text-muted">{icon}</div>}
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
      className={`h-8 rounded-md border border-line bg-surface px-2 text-[13px] outline-none hover:bg-surface2 focus:border-accent ${className}`}
    >
      {children}
    </select>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="rounded border border-line bg-surface2 px-1.5 py-0.5 font-mono text-[10px] text-muted">{children}</kbd>;
}

export function ProbBar({ values, className = "" }: { values: { label: Label; value: number }[]; className?: string }) {
  return (
    <div className={`flex h-1.5 overflow-hidden rounded-full bg-surface2 ${className}`} role="img"
      aria-label={values.map((v) => `${LABEL_TEXT[v.label]} ${Math.round(v.value * 100)}%`).join(", ")}>
      {values.map((v) => <span key={v.label} style={{ width: `${v.value * 100}%`, background: LABEL_COLOR[v.label] }} />)}
    </div>
  );
}
