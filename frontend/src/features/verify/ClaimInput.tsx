import { ArrowUp, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";

export function ClaimInput({ running, onSubmit }: { running: boolean; onSubmit: (claim: string) => void }) {
  const [text, setText] = useState("");
  const valid = text.trim().length >= 3;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (valid && !running) onSubmit(text.trim());
  };

  return (
    <form onSubmit={submit} className="rounded-3xl border border-line bg-surface p-3 shadow-card focus-within:border-accent">
      <label htmlFor="claim" className="sr-only">Claim to verify</label>
      <textarea
        id="claim"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit(e);
        }}
        rows={3}
        maxLength={2000}
        placeholder="Paste a headline or claim to check against evidence..."
        className="w-full resize-none bg-transparent px-3 py-2 font-serif text-xl leading-snug text-ink outline-none placeholder:text-muted/70"
      />
      <div className="flex items-center justify-between px-3 pb-1 pt-2">
        <span className="text-xs text-muted">Ctrl + Enter to run</span>
        <button
          type="submit"
          disabled={!valid || running}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2 text-sm font-semibold text-accentink transition enabled:hover:brightness-110 disabled:opacity-40"
        >
          {running ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
          {running ? "Verifying" : "Verify"}
        </button>
      </div>
    </form>
  );
}
