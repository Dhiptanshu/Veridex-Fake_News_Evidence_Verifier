import { AssistantPage } from "@/features/assistant/AssistantPage";
import { BatchPage } from "@/features/batch/BatchPage";
import { ComparePage } from "@/features/compare/ComparePage";
import { DataPage } from "@/features/data/DataPage";
import { HistoryPage } from "@/features/history/HistoryPage";
import { InsightsPage } from "@/features/insights/InsightsPage";
import { PipelinePage } from "@/features/pipeline/PipelinePage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { VerifyPage } from "@/features/verify/VerifyPage";
import { useRoute } from "./routes";
import { Shell } from "./Shell";

export default function App() {
  const [route, go] = useRoute();
  return (
    <Shell route={route} go={go}>
      {/* The Verify tab stays mounted while you visit other tabs, so a running or finished verification is not lost. */}
      <div hidden={route !== "verify"}><VerifyPage go={go} /></div>
      {route === "assistant" && <AssistantPage />}
      {route === "compare" && <ComparePage />}
      {route === "batch" && <BatchPage />}
      {route === "history" && <HistoryPage go={go} />}
      {route === "data" && <DataPage />}
      {route === "insights" && <InsightsPage />}
      {route === "pipeline" && <PipelinePage />}
      {route === "settings" && <SettingsPage />}
    </Shell>
  );
}
