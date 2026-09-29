import type { PipelineEvent, StageInfo } from "./types";

export async function fetchStages(signal?: AbortSignal): Promise<StageInfo[]> {
  const res = await fetch("/api/stages", { signal });
  if (!res.ok) throw new Error(`Stage catalog failed: HTTP ${res.status}`);
  return res.json();
}

/** POSTs a claim and yields PipelineEvents as the server streams them (SSE framing over fetch). */
export async function* streamVerify(
  claim: string,
  options: Record<string, string>,
  signal?: AbortSignal,
): AsyncGenerator<PipelineEvent> {
  const res = await fetch("/api/verify/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claim, options }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Verification failed: HTTP ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const data = frame.split("\n").find((l) => l.startsWith("data: "));
      if (data) yield JSON.parse(data.slice(6)) as PipelineEvent;
    }
  }
}
