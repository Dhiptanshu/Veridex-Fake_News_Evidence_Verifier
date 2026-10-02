import { KeyRound, Sparkles } from "lucide-react";
import { Empty, Panel } from "@/components/ui";
import { ChatThread } from "./ChatThread";
import { useChatStatus } from "./AssistantPanel";

const STARTERS = [
  "Is it true that the government banned 500 rupee notes again?",
  "What did the Union Cabinet decide this week?",
  "Has this viral WhatsApp claim been fact-checked? Drinking hot water cures cancer",
  "Explain how you decide between refuted and not enough info",
];

/** A free-form assistant: no claim needed. It searches news, fact-checkers and Wikipedia and cites what it finds. */
export function AssistantPage() {
  const status = useChatStatus();
  if (status && !status.configured) {
    return (
      <Panel>
        <Empty icon={<KeyRound size={20} />} title="The assistant needs an LLM key">
          Add <code className="font-mono text-xs">FNEV_AICREDITS_API_KEY</code> to <code className="font-mono text-xs">backend/.env</code> and restart the API. See the Pipeline tab for the status of every service.
        </Empty>
      </Panel>
    );
  }
  return (
    <div className="mx-auto max-w-3xl">
      <Panel
        title={<span className="flex items-center gap-2"><Sparkles size={14} className="text-accent" />Ask anything</span>}
        subtitle="Searches news, fact-checkers and Wikipedia as needed, and cites every source."
      >
        <ChatThread
          context={null} initialSources={[]} resetKey="free" persistKey="free" suggestions={STARTERS} height="min-h-[26rem]"
          placeholder="Ask about a claim, an event or how this tool works..." modelHint={status?.model ? `Model: ${status.model}` : undefined}
        />
      </Panel>
    </div>
  );
}
