import { KeyRound, Sparkles } from "lucide-react";
import { useCallback, useState } from "react";
import { Empty, Panel } from "@/components/ui";
import { usePersistentState } from "@/lib/persist";
import { useChatStatus } from "./AssistantPanel";
import { ChatThread, type SavedMsg } from "./ChatThread";
import { SessionMenu, type SessionMeta } from "./SessionMenu";

const STARTERS = [
  "Is it true that the government banned 500 rupee notes again?",
  "What did the Union Cabinet decide this week?",
  "Has this viral WhatsApp claim been fact-checked? Drinking hot water cures cancer",
  "Explain how you decide between refuted and not enough info",
];
const MAX_SESSIONS = 50;
const newId = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
const chatKey = (id: string) => `fnev-chat:session:${id}`;
const dropStored = (id: string) => { try { localStorage.removeItem(chatKey(id)); } catch { /* ignore */ } };

/**
 * A free-form assistant with saved chat sessions. Opening the app (or reloading) starts a fresh chat; while you use the app
 * it stays on the chat you are in, and "Recent chats" reopens any earlier one.
 */
export function AssistantPage() {
  const status = useChatStatus();
  const [sessions, setSessions] = usePersistentState<SessionMeta[]>("fnev-sessions", []);
  const [currentId, setCurrentId] = useState(newId);  // a new chat on every page load; it is only saved once you send a message

  const onChange = useCallback((msgs: SavedMsg[]) => {
    const first = msgs.find((m) => m.role === "user");
    if (!first) return;
    setSessions((all) => {
      const old = all.find((s) => s.id === currentId);
      const meta: SessionMeta = { id: currentId, title: old?.title ?? (first.content.replace(/\s+/g, " ").trim().slice(0, 70) || "New chat"), updatedAt: Date.now(), count: msgs.length };
      const next = [meta, ...all.filter((s) => s.id !== currentId)];
      next.slice(MAX_SESSIONS).forEach((s) => dropStored(s.id));  // keep the most recent MAX_SESSIONS chats
      return next.slice(0, MAX_SESSIONS);
    });
  }, [currentId, setSessions]);

  const remove = (id: string) => {
    dropStored(id);
    setSessions((all) => all.filter((s) => s.id !== id));
    if (id === currentId) setCurrentId(newId());
  };
  const removeAll = () => { sessions.forEach((s) => dropStored(s.id)); setSessions([]); setCurrentId(newId()); };
  const startNew = () => { if (sessions.some((s) => s.id === currentId)) setCurrentId(newId()); };  // an unsent chat is already "new"

  if (status && !status.configured) {
    return (
      <Panel>
        <Empty icon={<KeyRound size={20} />} title="The assistant needs an LLM key">
          Add <code className="font-mono text-xs">FNEV_AICREDITS_API_KEY</code> to <code className="font-mono text-xs">backend/.env</code> and restart the API. See the Pipeline tab for the status of every service.
        </Empty>
      </Panel>
    );
  }
  const current = sessions.find((s) => s.id === currentId);
  return (
    <div className="mx-auto max-w-3xl">
      <Panel
        title={<span className="flex items-center gap-2"><Sparkles size={14} className="text-accent" />{current ? current.title : "New chat"}</span>}
        subtitle="Searches news, fact-checkers and Wikipedia as needed, and cites every source."
        actions={<SessionMenu sessions={sessions} currentId={currentId} onOpen={setCurrentId} onDelete={remove} onDeleteAll={removeAll} onNew={startNew} />}
      >
        <ChatThread
          key={currentId} context={null} initialSources={[]} resetKey={currentId} persistKey={`session:${currentId}`} onChange={onChange}
          suggestions={STARTERS} height="min-h-[26rem]"
          placeholder="Ask about a claim, an event or how this tool works..." modelHint={status?.model ? `Model: ${status.model}` : undefined}
        />
      </Panel>
    </div>
  );
}
