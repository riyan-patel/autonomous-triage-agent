"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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

function githubUrl(item) {
  return `https://github.com/${item.repo_full_name}/issues/${item.issue_number}`;
}

function decisionLabel(item) {
  if (item.action_type === "act") return { text: "auto-applied", cls: "act" };
  if (item.review_decision === "rejected") return { text: "rejected", cls: "rejected" };
  if (item.review_decision === "approved") {
    return item.executed
      ? { text: "approved · executed", cls: "approved_execute" }
      : { text: "approved", cls: "approved" };
  }
  return { text: "needs review", cls: "escalate" };
}

function IssueLink({ item }) {
  return (
    <a href={githubUrl(item)} target="_blank" rel="noopener noreferrer">
      #{item.issue_number} {item.title}
      <span className="external-link-icon">↗</span>
    </a>
  );
}

export default function DashboardPage() {
  const [items, setItems] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingReview, setPendingReview] = useState(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState(null);

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
      const data = await res.json();
      if (data.execution === "trigger_failed") {
        setError(
          `Decision recorded, but execution didn't trigger (${data.execution_error}). ` +
            "webhook-ingress may not be reachable."
        );
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setPendingReview(null);
    }
  }

  const needsReview = useMemo(
    () => items.filter((item) => item.action_type === "escalate" && !item.review_decision),
    [items]
  );

  const activityItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      if (filter === "acted" && item.action_type !== "act") return false;
      if (filter === "escalated" && item.action_type !== "escalate") return false;
      if (filter === "approved" && item.review_decision !== "approved") return false;
      if (filter === "rejected" && item.review_decision !== "rejected") return false;
      if (!q) return true;
      const payload = item.payload || {};
      const haystack = `${item.repo_full_name} ${item.title} ${payload.summary || ""}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [items, search, filter]);

  return (
    <main className="page">
      <div className="header">
        <div>
          <h1>Triage Queue</h1>
          <p className="subtitle">
            Live agent triage decisions — autonomous actions and items escalated for human review.
          </p>
        </div>
      </div>

      {metrics && (
        <div className="metrics">
          <MetricCard label="Issues handled" value={metrics.totalIssuesHandled} />
          <MetricCard label="Acted automatically" value={metrics.actedCount} />
          <MetricCard label="Escalated" value={metrics.escalatedCount} />
          <MetricCard label="Escalation rate" value={formatPercent(metrics.escalationRate)} />
          <MetricCard label="Avg confidence" value={formatConfidence(metrics.avgConfidence)} />
        </div>
      )}

      {error && <p className="error-banner">{error}</p>}

      {!loading && (
        <>
          <div className="section-heading">
            <h2>Needs your review</h2>
            {needsReview.length > 0 && <span className="count-pill">{needsReview.length}</span>}
          </div>

          {needsReview.length === 0 ? (
            <p className="empty-review">Nothing waiting on you right now.</p>
          ) : (
            <div className="review-cards">
              {needsReview.map((item) => {
                const payload = item.payload || {};
                return (
                  <div className="review-card" key={item.action_id}>
                    <div className="review-card-top">
                      <div className="review-card-issue">
                        <IssueLink item={item} />
                        <div className="repo">{item.repo_full_name}</div>
                      </div>
                      <div className="review-card-actions">
                        <button
                          className="btn approve"
                          disabled={pendingReview === item.action_id}
                          onClick={() => review(item.action_id, "approved")}
                        >
                          Approve
                        </button>
                        <button
                          className="btn reject"
                          disabled={pendingReview === item.action_id}
                          onClick={() => review(item.action_id, "rejected")}
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                    <div className="review-card-summary">{payload.summary}</div>
                    {payload.draft_reply && (
                      <div className="review-card-reply">
                        <div className="reply-label">Proposed reply</div>
                        {payload.draft_reply}
                      </div>
                    )}
                    <div className="review-card-meta">
                      {(payload.labels || []).length > 0 && (
                        <div className="labels">
                          {payload.labels.map((label) => (
                            <span key={label}>{label}</span>
                          ))}
                        </div>
                      )}
                      <span style={{ color: "var(--muted-2)", fontSize: 12.5 }}>
                        confidence {formatConfidence(item.confidence)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="section-heading" style={{ marginTop: 12 }}>
            <h2>Activity</h2>
          </div>

          <div className="toolbar">
            <input
              className="search-input"
              placeholder="Search by repo, issue, or summary..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="filter-chips">
              {[
                ["all", "All"],
                ["acted", "Acted"],
                ["escalated", "Escalated"],
                ["approved", "Approved"],
                ["rejected", "Rejected"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  className={`chip ${filter === key ? "active" : ""}`}
                  onClick={() => setFilter(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {activityItems.length === 0 ? (
            <p className="empty">No matching triage decisions.</p>
          ) : (
            <div className="activity-list">
              {activityItems.map((item) => {
                const payload = item.payload || {};
                const decision = decisionLabel(item);
                const key = `${item.repo_full_name}#${item.issue_number}`;
                const isExpanded = expandedId === key;
                return (
                  <div key={key}>
                    <div className="activity-row" onClick={() => setExpandedId(isExpanded ? null : key)}>
                      <div className="issue-cell">
                        <IssueLink item={item} />
                        <div className="repo">{item.repo_full_name}</div>
                      </div>
                      <div className="summary-cell">{payload.summary || "—"}</div>
                      <div className="labels">
                        {(payload.labels || []).map((label) => (
                          <span key={label}>{label}</span>
                        ))}
                      </div>
                      <div className="confidence-cell">{formatConfidence(item.confidence)}</div>
                      <div>
                        <span className={`badge ${decision.cls}`}>{decision.text}</span>
                      </div>

                      {isExpanded && (
                        <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
                          <div className="detail-grid">
                            <div className="detail-field">
                              <div className="field-label">Type</div>
                              <div className="field-value">{payload.type || "—"}</div>
                            </div>
                            <div className="detail-field">
                              <div className="field-label">Severity</div>
                              <div className="field-value">{payload.severity || "—"}</div>
                            </div>
                            <div className="detail-field">
                              <div className="field-label">Suggested reviewer</div>
                              <div className="field-value">{payload.suggested_reviewer || "—"}</div>
                            </div>
                            <div className="detail-field">
                              <div className="field-label">Duplicate of</div>
                              <div className="field-value">
                                {payload.duplicate_of ? `#${payload.duplicate_of}` : "—"}
                              </div>
                            </div>
                            <div className="detail-field">
                              <div className="field-label">Mode</div>
                              <div className="field-value">{item.dry_run ? "Dry run" : "Live"}</div>
                            </div>
                            {item.reviewer && (
                              <div className="detail-field">
                                <div className="field-label">Reviewed by</div>
                                <div className="field-value">{item.reviewer}</div>
                              </div>
                            )}
                          </div>
                          {payload.draft_reply && (
                            <div className="detail-reply">{payload.draft_reply}</div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {loading && <p className="empty">Loading...</p>}
    </main>
  );
}
