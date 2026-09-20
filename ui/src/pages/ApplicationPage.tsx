import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import DecisionChip from "../components/DecisionChip";
import ErrorBanner from "../components/ErrorBanner";
import Skeleton from "../components/Skeleton";
import SourceBadge from "../components/SourceBadge";
import { api, ApiError } from "../lib/api";
import {
  formatConfidence,
  formatCost,
  formatDateTime,
  formatLatency,
} from "../lib/format";
import type {
  Application,
  HumanDecision,
  ReviewItem,
  TriageResult,
} from "../lib/types";
import { useAsync } from "../lib/useAsync";

const ACTOR_STORAGE_KEY = "duta.actor";

function loadActor(): string {
  try {
    return localStorage.getItem(ACTOR_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveActor(name: string): void {
  try {
    localStorage.setItem(ACTOR_STORAGE_KEY, name);
  } catch {
    // storage unavailable — the field still works for this session
  }
}

export default function ApplicationPage() {
  const { id } = useParams<{ id: string }>();
  const detail = useAsync(() => api.application(id ?? ""), [id]);

  return (
    <div className="page">
      <Link to="/" className="back-link">
        &larr; Back to queue
      </Link>

      {detail.error && (
        <ErrorBanner message={detail.error} onRetry={detail.retry} />
      )}

      {detail.loading && <DetailSkeleton />}

      {!detail.loading && detail.data && (
        <>
          <PageHead application={detail.data.application} />
          <div className="detail-grid">
            <div className="detail-col">
              <CandidateCard application={detail.data.application} />
              <ResumeCard resumeText={detail.data.application.resume_text} />
            </div>
            <div className="detail-col">
              <TriagePanel triage={detail.data.triage} />
              <DecisionBox
                review={detail.data.review}
                onDecided={detail.retry}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function PageHead({ application }: { application: Application }) {
  return (
    <div className="detail-head">
      <h1 className="detail-name">{application.candidate_name}</h1>
      <div className="detail-subtitle">
        <span>{application.position_title ?? "Position not specified"}</span>
        {application.position_code && (
          <span className="ref">{application.position_code}</span>
        )}
        <SourceBadge source={application.source} />
        <span className="ref">{application.source_ref}</span>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="field-row">
      <dt>{label}</dt>
      <dd className={value ? undefined : "missing"}>{value ?? "Not provided"}</dd>
    </div>
  );
}

function CandidateCard({ application }: { application: Application }) {
  return (
    <section className="card">
      <h2 className="card-title">Candidate</h2>
      <dl className="field-list">
        <Field label="Email" value={application.email} />
        <Field label="Phone" value={application.phone} />
        <Field label="Location" value={application.location_raw} />
        <Field label="Work authorization" value={application.work_auth} />
        <Field
          label="Source"
          value={`${application.source} · ${application.source_ref}`}
        />
        <Field
          label="Submitted"
          value={
            application.submitted_at
              ? formatDateTime(application.submitted_at)
              : null
          }
        />
      </dl>
    </section>
  );
}

function ResumeCard({ resumeText }: { resumeText: string | null }) {
  return (
    <section className="card">
      <h2 className="card-title">Resume</h2>
      {resumeText ? (
        <pre className="resume-text">{resumeText}</pre>
      ) : (
        <p className="missing">No resume text captured for this application.</p>
      )}
    </section>
  );
}

function evidenceValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  return JSON.stringify(value);
}

function TriagePanel({ triage }: { triage: TriageResult | null }) {
  if (!triage) {
    return (
      <section className="card">
        <h2 className="card-title">Machine triage</h2>
        <p className="missing">No triage result recorded yet.</p>
      </section>
    );
  }

  const evidenceEntries = triage.evidence
    ? Object.entries(triage.evidence)
    : [];

  return (
    <section className="card">
      <div className="card-title-row">
        <h2 className="card-title">Machine triage</h2>
        <DecisionChip decision={triage.decision} />
      </div>

      {triage.rationale && <p className="rationale">{triage.rationale}</p>}

      {evidenceEntries.length > 0 && (
        <>
          <h3 className="subhead">Evidence</h3>
          <dl className="kv-list">
            {evidenceEntries.map(([key, value]) => (
              <div className="kv-row" key={key}>
                <dt>{key}</dt>
                <dd>{evidenceValue(value)}</dd>
              </div>
            ))}
          </dl>
        </>
      )}

      <dl className="meta-grid">
        <div>
          <dt>Engine</dt>
          <dd className="ref">{triage.engine}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{formatConfidence(triage.confidence)}</dd>
        </div>
        <div>
          <dt>Cost</dt>
          <dd>{formatCost(triage.cost_usd)}</dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd>{formatLatency(triage.latency_ms)}</dd>
        </div>
      </dl>
    </section>
  );
}

const DECISIONS: Array<{ value: HumanDecision; sub: string }> = [
  { value: "ADVANCE", sub: "Shortlist for the requisition" },
  { value: "NEEDS_INFO", sub: "Draft an info request" },
  { value: "DUPLICATE", sub: "Link to the existing record" },
  { value: "REJECT", sub: "Decline this application" },
];

function DecisionBox({
  review,
  onDecided,
}: {
  review: ReviewItem | null;
  onDecided: () => void;
}) {
  const [selected, setSelected] = useState<HumanDecision | null>(null);
  const [note, setNote] = useState("");
  const [actor, setActor] = useState(loadActor);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [noteError, setNoteError] = useState(false);
  const [done, setDone] = useState<HumanDecision | null>(null);

  if (!review) {
    return (
      <section className="card">
        <h2 className="card-title">Your decision</h2>
        <p className="missing">
          This application has no review-queue item, so there is nothing to
          decide here.
        </p>
      </section>
    );
  }

  if (done) {
    return (
      <section className="card decision-done">
        <div className="done-check" aria-hidden="true" />
        <h2 className="card-title">Decision recorded</h2>
        <p className="done-line">
          <DecisionChip decision={done} /> by {actor.trim()}
        </p>
        <Link to="/" className="btn btn-primary">
          Back to queue
        </Link>
      </section>
    );
  }

  if (review.status !== "open") {
    return (
      <section className="card">
        <h2 className="card-title">Your decision</h2>
        <p className="decided-line">
          {review.human_decision && (
            <DecisionChip decision={review.human_decision} />
          )}
          <span>
            Decided by {review.decided_by ?? "—"} ·{" "}
            {formatDateTime(review.decided_at)}
          </span>
        </p>
        <Link to="/" className="btn btn-ghost">
          Back to queue
        </Link>
      </section>
    );
  }

  const canSubmit =
    selected !== null && actor.trim().length > 0 && !submitting;

  async function submit() {
    if (!review || selected === null) return;
    if (selected === "REJECT" && note.trim().length === 0) {
      setNoteError(true);
      return;
    }
    setNoteError(false);
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.decide(review.id, {
        decision: selected,
        actor: actor.trim(),
        note: note.trim(),
      });
      setDone(selected);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict(true);
        setSubmitError(
          "This item was already decided by someone else. Refresh to see the outcome.",
        );
      } else {
        setSubmitError(err instanceof Error ? err.message : "Request failed.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2 className="card-title">Your decision</h2>
      <p className="escalation-reason">
        <span className="escalation-label">Escalated because</span>
        {review.reason}
      </p>

      <div className="decision-grid" role="group" aria-label="Decision">
        {DECISIONS.map(({ value, sub }) => (
          <button
            key={value}
            type="button"
            className={[
              "decision-btn",
              `decision-${value.toLowerCase()}`,
              selected === value ? "selected" : "",
            ]
              .join(" ")
              .trim()}
            aria-pressed={selected === value}
            onClick={() => {
              setSelected(value);
              if (value !== "REJECT") setNoteError(false);
            }}
            disabled={submitting}
          >
            <span className="d-label">{value.replace(/_/g, " ")}</span>
            <span className="d-sub">{sub}</span>
          </button>
        ))}
      </div>

      {selected === "REJECT" && (
        <p className="reject-hint">
          Negative decisions are human-only and always audited.
        </p>
      )}

      <div className={noteError ? "form-field invalid" : "form-field"}>
        <label htmlFor="decision-note">
          Note{selected === "REJECT" ? " (required for REJECT)" : ""}
        </label>
        <textarea
          id="decision-note"
          rows={3}
          placeholder="Context for the audit trail…"
          value={note}
          onChange={(e) => {
            setNote(e.target.value);
            if (e.target.value.trim().length > 0) setNoteError(false);
          }}
          disabled={submitting}
        />
        {noteError && (
          <p className="form-error">A note is required to reject.</p>
        )}
      </div>

      <div className="form-field">
        <label htmlFor="decision-actor">Your name</label>
        <input
          id="decision-actor"
          type="text"
          placeholder="Recorded as the deciding recruiter"
          value={actor}
          onChange={(e) => {
            setActor(e.target.value);
            saveActor(e.target.value);
          }}
          disabled={submitting}
        />
      </div>

      {submitError && (
        <div className="submit-error" role="alert">
          <span>{submitError}</span>
          {conflict && (
            <button type="button" className="btn btn-ghost" onClick={onDecided}>
              Refresh
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        className={
          selected === "REJECT" ? "btn btn-danger submit-btn" : "btn btn-primary submit-btn"
        }
        disabled={!canSubmit}
        onClick={() => void submit()}
      >
        {submitting ? "Recording…" : "Record decision"}
      </button>
    </section>
  );
}

function DetailSkeleton() {
  return (
    <div className="detail-grid" aria-busy="true">
      <div className="detail-col">
        <div className="card">
          <Skeleton height={22} width="45%" />
          <Skeleton height={14} width="80%" />
          <Skeleton height={14} width="70%" />
          <Skeleton height={14} width="75%" />
          <Skeleton height={14} width="60%" />
        </div>
        <div className="card">
          <Skeleton height={22} width="30%" />
          <Skeleton height={260} width="100%" />
        </div>
      </div>
      <div className="detail-col">
        <div className="card">
          <Skeleton height={22} width="50%" />
          <Skeleton height={14} width="85%" />
          <Skeleton height={14} width="70%" />
        </div>
        <div className="card">
          <Skeleton height={22} width="40%" />
          <Skeleton height={110} width="100%" />
          <Skeleton height={38} width="100%" />
        </div>
      </div>
    </div>
  );
}
