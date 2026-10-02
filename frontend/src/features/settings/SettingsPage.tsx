import { Monitor, Moon, Sun } from "lucide-react";
import { Button, Panel, Segmented } from "@/components/ui";
import { countChanged, OptionsGrid, useStageCatalog } from "@/features/verify/OptionsPanel";
import { useAppState } from "@/state/AppState";
import { useTheme, type ThemeMode } from "@/theme/ThemeProvider";

export function SettingsPage() {
  const { mode, setMode } = useTheme();
  const { defaults, setDefaults, history, clearHistory } = useAppState();
  const catalog = useStageCatalog();

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Panel title="Appearance">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[13px] font-medium">Theme</p>
            <p className="text-xs text-muted">System follows your operating system setting.</p>
          </div>
          <Segmented<ThemeMode>
            ariaLabel="Theme" value={mode} onChange={setMode}
            options={[
              { value: "system", label: <span className="flex items-center gap-1.5"><Monitor size={13} />System</span> },
              { value: "light", label: <span className="flex items-center gap-1.5"><Sun size={13} />Light</span> },
              { value: "dark", label: <span className="flex items-center gap-1.5"><Moon size={13} />Dark</span> },
            ]}
          />
        </div>
      </Panel>

      <Panel
        title="Default pipeline"
        actions={countChanged(defaults) > 0 ? <button onClick={() => setDefaults({})} className="text-xs text-accent hover:underline">Reset</button> : null}
      >
        <p className="mb-3 text-xs text-muted">Used as the starting options in Verify. You can still change them per run.</p>
        <OptionsGrid value={defaults} onChange={setDefaults} stages={catalog} />
      </Panel>

      <Panel title="Data on this device">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[13px] font-medium">Saved runs</p>
            <p className="text-xs text-muted">{history.length} run{history.length === 1 ? "" : "s"} stored in this browser only (localStorage). Nothing is uploaded.</p>
          </div>
          <Button disabled={!history.length} onClick={() => { if (confirm(`Delete all ${history.length} saved runs?`)) clearHistory(); }}>Clear history</Button>
        </div>
      </Panel>

      <Panel title="Privacy" subtitle="What leaves this device, and when">
        <ul className="space-y-2 text-[13px] leading-relaxed text-muted">
          <li><b className="font-semibold text-ink">Searching:</b> short search queries derived from your claim go to the news and fact-check providers (GNews, NewsAPI, Google Fact Check) and to Wikipedia for background. Public article pages found by search are downloaded to read them.</li>
          <li><b className="font-semibold text-ink">AI judge and Vera:</b> your claim, the evidence passages shown on screen and your chat messages are sent to AICredits, and on to the model provider it routes to, to write verdicts and answers.</li>
          <li><b className="font-semibold text-ink">On this device:</b> history, chats, results and settings are stored only in this browser. Nothing is uploaded.</li>
          <li><b className="font-semibold text-ink">Offline mode</b> (no keys configured) sends nothing anywhere.</li>
        </ul>
      </Panel>

      <Panel title="About">
        <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-[13px]">
          <dt className="text-muted">Project</dt><dd>Veridex, an evidence-based fact-checker (NLP Lab, Semester VII). Meet Vera, the assistant.</dd>
          <dt className="text-muted">Reports</dt><dd className="font-mono text-xs">docs/REPORT.md, docs/DEMO.md, docs/API_KEYS.md</dd>
          <dt className="text-muted">Results</dt><dd className="font-mono text-xs">docs/results/*.json (shown in Insights)</dd>
          <dt className="text-muted">Keyboard</dt><dd><span className="font-mono text-xs">Enter</span> runs a claim, <span className="font-mono text-xs">Shift+Enter</span> adds a line.</dd>
        </dl>
      </Panel>
    </div>
  );
}
