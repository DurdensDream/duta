import { Link } from "react-router-dom";
import ErrorBanner from "../components/ErrorBanner";
import Skeleton from "../components/Skeleton";
import SourceBadge from "../components/SourceBadge";
import { api } from "../lib/api";
import { formatCount, formatPercent, waitingSince } from "../lib/format";
import type { QueueItem, Stats } from "../lib/types";
import { useAsync } from "../lib/useAsync";

export default function QueuePage() {
  const stats = useAsync(() => api.stats(), []);
  const queue = useAsync(() => api.queue("open", 100), []);

  const anyError = stats.error ?? queue.error;
  const retryAll = () => {
    if (stats.error) stats.retry();
    if (queue.error) queue.retry();
  };

  return (
    <div className="page">
      {anyError && <ErrorBanner message={anyError} onRetry={retryAll} />}

      <StatsBar stats={stats.data} loading={stats.loading} />

      <section className="queue-section" aria-label="Open reviews">
        <div className="section-head">
          <h2 className="section-title">
            Open reviews
            {queue.data && (
              <span className="count-pill">{formatCount(queue.data.count)}</span>
            )}
          </h2>
          <p className="section-note">
            Oldest first — the queue is never score-ordered.
          </p>
        </div>

        {queue.loading ? (
          <QueueSkeleton />
        ) : queue.error ? null : queue.data && queue.data.items.length === 0 ? (
          <EmptyQueue />
        ) : (
          queue.data && <QueueList items={queue.data.items} />
        )}
      </section>
    </div>
  );
}

function StatsBar({ stats, loading }: { stats: Stats | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="stats-bar" aria-busy="true">
        {[0, 1, 2, 3].map((i) => (
          <div className="stat-tile" key={i}>
            <Skeleton height={13} width="60%" />
            <Skeleton height={30} width="45%" className="stat-skeleton-value" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="stats-bar">
      <StatTile
        label="Applications"
        value={stats ? formatCount(stats.applications) : "—"}
        sub="ingested across all sources"
      />
      <StatTile
        label="Triaged"
        value={stats ? formatCount(stats.triaged) : "—"}
        sub="received a machine decision"
      />
      <StatTile
        label="Auto-resolution rate"
        value={stats ? formatPercent(stats.auto_resolution_rate) : "—"}
        sub="resolved without human touch"
      />
      <StatTile
        label="Open reviews"
        value={stats ? formatCount(stats.open_reviews) : "—"}
        sub="waiting on a recruiter"
      />
    </div>
  );
}

function StatTile({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="stat-tile">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  );
}

function QueueList({ items }: { items: QueueItem[] }) {
  return (
    <div className="queue-card">
      <div className="queue-row queue-header" aria-hidden="true">
        <span>Source</span>
        <span>Ref</span>
        <span>Candidate</span>
        <span>Position</span>
        <span>Reason</span>
        <span className="wait-col">Waiting</span>
      </div>
      {items.map((item) => (
        <Link
          key={item.id}
          to={`/application/${item.application_id}`}
          className="queue-row queue-item"
        >
          <span>
            <SourceBadge source={item.source} />
          </span>
          <span className="ref">{item.source_ref}</span>
          <span className="candidate">{item.candidate_name}</span>
          <span className="position">{item.position_title}</span>
          <span className="reason" title={item.reason}>
            {item.reason}
          </span>
          <span className="wait-col waiting">{waitingSince(item.created_at)}</span>
        </Link>
      ))}
    </div>
  );
}

function QueueSkeleton() {
  return (
    <div className="queue-card" aria-busy="true">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div className="queue-row" key={i}>
          <Skeleton height={22} width={76} />
          <Skeleton height={14} width={84} />
          <Skeleton height={14} width="70%" />
          <Skeleton height={14} width="65%" />
          <Skeleton height={14} width="85%" />
          <Skeleton height={14} width={52} />
        </div>
      ))}
    </div>
  );
}

function EmptyQueue() {
  return (
    <div className="empty">
      <div className="empty-art" aria-hidden="true">
        <div className="empty-check" />
      </div>
      <h3 className="empty-title">Queue is clear</h3>
      <p className="empty-sub">
        No open reviews right now. New escalations will appear here, oldest first.
      </p>
    </div>
  );
}
