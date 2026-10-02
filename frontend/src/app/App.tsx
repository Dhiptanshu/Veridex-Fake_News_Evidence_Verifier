import { useEffect, useState, type ReactNode } from "react";
import { AssistantPage } from "@/features/assistant/AssistantPage";
import { BatchPage } from "@/features/batch/BatchPage";
import { ComparePage } from "@/features/compare/ComparePage";
import { DataPage } from "@/features/data/DataPage";
import { HistoryPage } from "@/features/history/HistoryPage";
import { InsightsPage } from "@/features/insights/InsightsPage";
import { PipelinePage } from "@/features/pipeline/PipelinePage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { VerifyPage } from "@/features/verify/VerifyPage";
import { useRoute, type Route } from "./routes";
import { Shell } from "./Shell";

export default function App() {
  const [route, go] = useRoute();
  // A tab is mounted the first time it is opened and then kept (hidden), so typed text, results, chats and running
  // batches survive tab switches. Everything important is also persisted to localStorage to survive reloads.
  const [visited, setVisited] = useState<Set<Route>>(() => new Set<Route>(["verify", route]));
  useEffect(() => setVisited((v) => (v.has(route) ? v : new Set(v).add(route))), [route]);

  const page = (r: Route, node: ReactNode) => visited.has(r) && <div key={r} hidden={route !== r}>{node}</div>;
  return (
    <Shell route={route} go={go}>
      {page("verify", <VerifyPage go={go} />)}
      {page("assistant", <AssistantPage />)}
      {page("compare", <ComparePage />)}
      {page("batch", <BatchPage />)}
      {page("history", <HistoryPage go={go} />)}
      {page("data", <DataPage />)}
      {page("insights", <InsightsPage />)}
      {page("pipeline", <PipelinePage />)}
      {page("settings", <SettingsPage />)}
    </Shell>
  );
}
