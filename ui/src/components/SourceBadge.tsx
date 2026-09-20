const KNOWN_SOURCES = new Set(["kestrel", "jobwire", "talentbase"]);

export default function SourceBadge({ source }: { source: string }) {
  const variant = KNOWN_SOURCES.has(source) ? source : "other";
  return <span className={`badge badge-${variant}`}>{source}</span>;
}
