const KNOWN_DECISIONS = new Set([
  "REVIEW",
  "ADVANCE",
  "NEEDS_INFO",
  "DUPLICATE",
  "REJECT",
]);

export default function DecisionChip({ decision }: { decision: string }) {
  const variant = KNOWN_DECISIONS.has(decision)
    ? decision.toLowerCase()
    : "other";
  return (
    <span className={`chip chip-${variant}`}>{decision.replace(/_/g, " ")}</span>
  );
}
