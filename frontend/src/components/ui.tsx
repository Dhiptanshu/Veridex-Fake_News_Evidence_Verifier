import { Check, ChevronDown, Loader2 } from "lucide-react";
import {
  Children, isValidElement, useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState,
  type ButtonHTMLAttributes, type CSSProperties, type ReactElement, type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import type { Label } from "@/api/types";

/** Shared primitives: glowing cards, pill badges, custom dropdowns, gradient primary buttons. */

export function Panel({
  title, actions, children, className = "", flush = false, subtitle, tint,
}: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; flush?: boolean; tint?: string;
}) {
  return (
    <section className={`card rounded-[22px] ${className}`} style={tint ? ({ "--tint": tint } as CSSProperties) : undefined}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-5 pt-4">
          <div className="min-w-0">
            <h3 className="font-display text-[14.5px] font-semibold leading-tight tracking-tight">{title}</h3>
            {subtitle && <p className="mt-0.5 text-[12px] text-muted">{subtitle}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        </header>
      )}
      <div className={flush ? "pt-2.5" : "p-5 pt-3"}>{children}</div>
    </section>
  );
}

/** A KPI tile: tinted icon, big number, label and a line of detail. */
export function StatCard({
  icon, value, unit, label, hint, tint = "var(--accent)",
}: { icon: ReactNode; value: ReactNode; unit?: string; label: string; hint?: ReactNode; tint?: string }) {
  return (
    <div className="card flex items-center gap-3.5 rounded-[20px] p-4" style={{ "--tint": tint } as CSSProperties}>
      <span className="grid size-11 shrink-0 place-items-center rounded-xl" style={{ background: `color-mix(in srgb, ${tint} 16%, transparent)`, color: tint }}>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="font-display text-[26px] font-semibold leading-none tracking-tight tabular-nums">
          {value}{unit && <span className="ml-1 text-sm font-medium text-muted">{unit}</span>}
        </p>
        <p className="mt-1.5 truncate text-[13px] font-medium">{label}</p>
        {hint && <p className="truncate text-xs text-muted">{hint}</p>}
      </div>
    </div>
  );
}

type Tone = "neutral" | "supported" | "refuted" | "accent" | "warn";
const TONES: Record<Tone, string> = {
  neutral: "bg-surface2 text-muted",
  supported: "bg-supported/14 text-supported",
  refuted: "bg-refuted/14 text-refuted",
  accent: "bg-accent/14 text-accent",
  warn: "bg-warn/16 text-warn",
};

export function Badge({ tone = "neutral", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11.5px] font-semibold leading-4 ${TONES[tone]} ${className}`}>{children}</span>;
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
    primary: "bg-accent text-accentink shadow-brand hover:brightness-110 active:brightness-95",
    secondary: "border border-line bg-surface hover:bg-surface2",
    ghost: "text-muted hover:bg-surface2 hover:text-ink",
  }[variant];
  const sz = size === "sm" ? "h-8 px-3 text-[12px]" : "h-10 px-4 text-[13px]";
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={`inline-flex shrink-0 items-center justify-center gap-2 rounded-xl font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${sz} ${v} ${className}`}
    >
      {loading ? <Loader2 size={15} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}

export function Segmented<T extends string>({
  value, onChange, options, ariaLabel,
}: { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; ariaLabel?: string }) {
  return (
    <div role="group" aria-label={ariaLabel} className="inline-flex rounded-2xl border border-line bg-surface2/70 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={`rounded-lg px-3 py-1.5 text-[12px] font-semibold transition ${value === o.value ? "bg-accent text-accentink shadow-brand" : "text-muted hover:text-ink"}`}
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
    <div role="tablist" className="inline-flex max-w-full gap-1 overflow-x-auto rounded-2xl border border-line bg-surface2/70 p-1">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={`shrink-0 rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition ${value === t.value ? "bg-accent text-accentink shadow-brand" : "text-muted hover:text-ink"}`}
        >
          {t.label}
          {t.count !== undefined && <span className={`ml-2 rounded-full px-1.5 text-[11px] ${value === t.value ? "bg-white/25" : "bg-accent/14 text-accent"}`}>{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div>
      <p className="text-[11.5px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function Empty({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      {icon && <div className="grid size-14 place-items-center rounded-2xl bg-accent/12 text-accent">{icon}</div>}
      <p className="font-display text-[16px] font-semibold">{title}</p>
      {children && <p className="max-w-md text-[13px] text-muted">{children}</p>}
      {action}
    </div>
  );
}

/* ------------------------------------------------------------------------------------------------------------------ */
/* Custom dropdown. Same API as a native <select> (children are <option> elements) but fully styled, keyboard accessible,
   and rendered in a portal so no panel can clip it. */

interface Opt { value: string; label: string }
function flatten(node: ReactNode): string {
  return Children.toArray(node).map((c) => (typeof c === "string" || typeof c === "number" ? String(c) : "")).join("");
}

export function Select({
  value, onChange, children, ariaLabel, className = "",
}: { value: string; onChange: (v: string) => void; children: ReactNode; ariaLabel?: string; className?: string }) {
  const options: Opt[] = useMemo(
    () => Children.toArray(children).filter(isValidElement).map((el) => {
      const e = el as ReactElement<{ value?: string; children?: ReactNode }>;
      const label = flatten(e.props.children);
      return { value: e.props.value !== undefined ? String(e.props.value) : label, label };
    }),
    [children],
  );
  const id = useId();
  const btn = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [pos, setPos] = useState<{ left: number; top?: number; bottom?: number; width: number; max: number } | null>(null);
  const current = options.find((o) => o.value === value);

  const place = useCallback(() => {
    const r = btn.current?.getBoundingClientRect();
    if (!r) return;
    const below = window.innerHeight - r.bottom;
    const above = r.top;
    const openUp = below < 220 && above > below;
    const width = Math.max(r.width, 220);
    setPos({
      left: Math.min(Math.max(8, r.left), window.innerWidth - width - 8), width,
      ...(openUp ? { bottom: window.innerHeight - r.top + 6 } : { top: r.bottom + 6 }),
      max: Math.max(160, Math.min(320, (openUp ? above : below) - 16)),
    });
  }, []);

  useLayoutEffect(() => { if (open) place(); }, [open, place]);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!list.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) setOpen(false); };
    const reflow = () => place();
    document.addEventListener("mousedown", close);
    window.addEventListener("resize", reflow);
    window.addEventListener("scroll", reflow, true);
    return () => { document.removeEventListener("mousedown", close); window.removeEventListener("resize", reflow); window.removeEventListener("scroll", reflow, true); };
  }, [open, place]);
  useEffect(() => { if (open) list.current?.querySelector<HTMLElement>("[data-active=true]")?.scrollIntoView({ block: "nearest" }); }, [open, active]);

  const choose = (v: string) => { onChange(v); setOpen(false); btn.current?.focus(); };
  const openMenu = () => { setActive(Math.max(0, options.findIndex((o) => o.value === value))); setOpen(true); };

  const onKey = (e: React.KeyboardEvent) => {
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); openMenu(); }
      return;
    }
    if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, options.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(options.length - 1); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(options[active]?.value ?? value); }
    else if (e.key === "Tab") setOpen(false);
  };

  return (
    <>
      <button
        ref={btn} type="button" role="combobox" aria-haspopup="listbox" aria-expanded={open} aria-controls={`${id}-list`} aria-label={ariaLabel}
        onClick={() => (open ? setOpen(false) : openMenu())} onKeyDown={onKey}
        className={`flex h-10 items-center justify-between gap-2 rounded-xl border bg-surface px-3.5 text-left text-[13px] font-medium outline-none transition ${open ? "border-accent ring-4 ring-accent/12" : "border-line hover:border-accent/50"} ${className}`}
      >
        <span className="truncate">{current?.label ?? value}</span>
        <ChevronDown size={16} className={`shrink-0 text-muted transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && pos && createPortal(
        <ul
          ref={list} id={`${id}-list`} role="listbox" onKeyDown={onKey}
          style={{ position: "fixed", left: pos.left, top: pos.top, bottom: pos.bottom, width: pos.width, maxHeight: pos.max }}
          className="rise z-[60] overflow-y-auto rounded-2xl border border-line bg-surface p-1.5 shadow-pop"
        >
          {options.map((o, i) => (
            <li
              key={o.value} role="option" aria-selected={o.value === value} data-active={i === active}
              onMouseEnter={() => setActive(i)} onMouseDown={(e) => { e.preventDefault(); choose(o.value); }}
              className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-[13px] ${i === active ? "bg-accent/12" : ""} ${o.value === value ? "font-semibold text-accent" : ""}`}
            >
              <span className="truncate">{o.label}</span>
              {o.value === value && <Check size={15} className="shrink-0" />}
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </>
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
      className="inline-grid shrink-0 place-items-center rounded-xl text-[12px] font-bold"
      style={{ width: size, height: size, background: `hsl(${h} 70% 55% / 0.18)`, color: `hsl(${h} 55% 42%)` }}
    >
      {initial}
    </span>
  );
}
