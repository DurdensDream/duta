/** "3h 12m", "2d 4h" — how long a queue item has been waiting. */
export function waitingSince(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m`;
  const days = Math.floor(hours / 24);
  if (days < 14) return `${days}d ${hours % 24}h`;
  return `${days}d`;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPercent(rate: number | null): string {
  if (rate === null) return "—";
  return `${(rate * 100).toFixed(1)}%`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatConfidence(confidence: number | null): string {
  if (confidence === null) return "—";
  if (confidence >= 0 && confidence <= 1) return `${Math.round(confidence * 100)}%`;
  return String(confidence);
}

export function formatCost(costUsd: number | null): string {
  if (costUsd === null) return "—";
  return `$${costUsd.toFixed(4)}`;
}

export function formatLatency(latencyMs: number | null): string {
  if (latencyMs === null) return "—";
  return `${formatCount(latencyMs)} ms`;
}
