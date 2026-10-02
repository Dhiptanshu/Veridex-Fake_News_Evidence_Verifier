import { useCallback, useEffect, useState } from "react";

export type Route = "verify" | "assistant" | "compare" | "batch" | "history" | "data" | "insights" | "pipeline" | "settings";
export const ROUTES: Route[] = ["verify", "assistant", "compare", "batch", "history", "data", "insights", "pipeline", "settings"];

function current(): Route {
  const h = location.hash.replace(/^#\/?/, "").split(/[/?]/)[0] as Route;
  return ROUTES.includes(h) ? h : "verify";
}

/** Tiny hash router: #/verify, #/history ... so every tab is linkable and the back button works. */
export function useRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState<Route>(current);
  useEffect(() => {
    const on = () => setRoute(current());
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  const go = useCallback((r: Route) => { location.hash = `#/${r}`; }, []);
  return [route, go];
}
