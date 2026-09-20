/** Shapes returned by the Duta API (services/duta/api.py). */

export interface Stats {
  applications: number;
  triaged: number;
  decisions: Record<string, number>;
  /** null when nothing has been triaged yet. */
  auto_resolution_rate: number | null;
  open_reviews: number;
}

export interface QueueItem {
  id: number;
  application_id: number;
  source: string;
  source_ref: string;
  candidate_name: string;
  position_title: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface QueueResponse {
  count: number;
  items: QueueItem[];
}

export interface Application {
  id: number;
  source: string;
  source_ref: string;
  candidate_name: string;
  email: string | null;
  phone: string | null;
  location_raw: string | null;
  work_auth: string | null;
  resume_text: string | null;
  position_title: string | null;
  position_code: string | null;
  submitted_at: string | null;
  payload_hash: string;
  ingested_at: string;
}

export interface TriageResult {
  id: number;
  application_id: number;
  decision: string;
  requisition_code: string | null;
  duplicate_of: number | null;
  confidence: number | null;
  evidence: Record<string, unknown> | null;
  rationale: string | null;
  engine: string;
  cost_usd: number | null;
  latency_ms: number | null;
  created_at: string;
}

export interface ReviewItem {
  id: number;
  application_id: number;
  reason: string;
  status: string;
  human_decision: string | null;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface ApplicationDetail {
  application: Application;
  triage: TriageResult | null;
  review: ReviewItem | null;
}

/** Decisions a human may take. The machine's action space has no REJECT (ADR-0004). */
export type HumanDecision = "ADVANCE" | "NEEDS_INFO" | "DUPLICATE" | "REJECT";

export interface DecideResponse {
  ok: boolean;
  application_id: number;
}
