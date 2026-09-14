"use client";

import { useCallback, useEffect, useState } from "react";

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

function formatPercent(x) {
  if (x === null || x === undefined) return "—";
  return `${Math.round(x * 100)}%`;
}

function formatConfidence(x) {
  if (x === null || x === undefined) return "—";
  return x.toFixed(2);
}

export default function DashboardPage() {
  const [items, setItems] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingReview, setPendingReview] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [queueRes, metricsRes] = await Promise.all([
        fetch("/api/queue"),
        fetch("/api/metrics"),
      ]);
      if (!queueRes.ok || !metricsRes.ok) {
        throw new Error("failed to load dashboard data");
      }
      const queueData = await queueRes.json();
      const metricsData = await metricsRes.json();
      setItems(queueData.items);
      setMetrics(metricsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function review(actionId, decision) {
    setPendingReview(actionId);
    try {
      const res = await fetch("/api/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: actionId, decision }),
      });
      if (!res.ok) throw new Error("review failed");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setPendingReview(null);
    }
  }

  return (
    <main className="page">
      <h1>Triage Queue</h1>
      <p className="subtitle">
        Live agent triage decisions - autonomous actions and items escalated for human review.
      </p>

      {metrics && (
        <div className="metrics">
          <MetricCard label="Issues handled" value={metrics.totalIssuesHandled} />
          <MetricCard label="Acted" value={metrics.actedCount} />
          <MetricCard label="Escalated" value={metrics.escalatedCount} />
          <MetricCard label="Escalation rate" value={formatPercent(metrics.escalationRate)} />
          <MetricCard label="Avg confidence" value={formatConfidence(metrics.avgConfidence)} />
        </div>
      )}

      {error && <p style={{ color: "var(--bad)" }}>{error}</p>}

      {loading ? (
        <p className="empty">Loading...</p>
      ) : items.length === 0 ? (
        <p className="empty">No triage decisions yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Issue</th>
              <th>Summary</th>
              <th>Labels</th>
              <th>Confidence</th>
              <th>Decision</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const payload = item.payload || {};
              const needsReview = item.action_type === "escalate" && !item.review_decision;
              return (
                <tr key={`${item.repo_full_name}#${item.issue_number}`}>
                  <td>
                    <div>{item.repo_full_name}</div>
                    <div style={{ color: "var(--muted)" }}>#{item.issue_number} {item.title}</div>
                  </td>
                  <td>{payload.summary || "—"}</td>
                  <td className="labels">
                    {(payload.labels || []).map((label) => (
                      <span key={label}>{label}</span>
                    ))}
                  </td>
                  <td>{formatConfidence(item.confidence)}</td>
                  <td>
                    <span className={`badge ${item.action_type}`}>{item.action_type}</span>
                  </td>
                  <td>
                    {item.review_decision ? (
                      <span className={`badge ${item.review_decision}`}>{item.review_decision}</span>
                    ) : needsReview ? (
                      <div className="review-actions">
                        <button
                          className="approve"
                          disabled={pendingReview === item.action_id}
                          onClick={() => review(item.action_id, "approved")}
                        >
                          Approve
                        </button>
                        <button
                          className="reject"
                          disabled={pendingReview === item.action_id}
                          onClick={() => review(item.action_id, "rejected")}
                        >
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span style={{ color: "var(--muted)" }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </main>
  );
}
