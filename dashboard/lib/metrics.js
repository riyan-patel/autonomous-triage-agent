// Pure aggregation over actions rows - kept separate from the DB-fetching
// API route so it's testable without a live Postgres connection.
export function computeMetrics(actions) {
  const total = actions.length;
  if (total === 0) {
    return {
      totalIssuesHandled: 0,
      actedCount: 0,
      escalatedCount: 0,
      escalationRate: 0,
      avgConfidence: null,
    };
  }

  const actedCount = actions.filter((a) => a.action_type === "act").length;
  const escalatedCount = actions.filter((a) => a.action_type === "escalate").length;
  const confidences = actions
    .map((a) => a.confidence)
    .filter((c) => typeof c === "number" && !Number.isNaN(c));

  return {
    totalIssuesHandled: total,
    actedCount,
    escalatedCount,
    escalationRate: escalatedCount / total,
    avgConfidence:
      confidences.length > 0
        ? confidences.reduce((sum, c) => sum + c, 0) / confidences.length
        : null,
  };
}
