import { describe, expect, it } from "vitest";
import { computeMetrics } from "../metrics.js";

describe("computeMetrics", () => {
  it("returns zeroed metrics for an empty action list", () => {
    const metrics = computeMetrics([]);
    expect(metrics).toEqual({
      totalIssuesHandled: 0,
      actedCount: 0,
      escalatedCount: 0,
      escalationRate: 0,
      avgConfidence: null,
    });
  });

  it("counts acted vs escalated and computes escalation rate", () => {
    const metrics = computeMetrics([
      { action_type: "act", confidence: 0.9 },
      { action_type: "act", confidence: 0.95 },
      { action_type: "escalate", confidence: 0.4 },
    ]);
    expect(metrics.totalIssuesHandled).toBe(3);
    expect(metrics.actedCount).toBe(2);
    expect(metrics.escalatedCount).toBe(1);
    expect(metrics.escalationRate).toBeCloseTo(1 / 3);
  });

  it("averages confidence, ignoring missing values", () => {
    const metrics = computeMetrics([
      { action_type: "act", confidence: 0.8 },
      { action_type: "act", confidence: null },
      { action_type: "act", confidence: 0.6 },
    ]);
    expect(metrics.avgConfidence).toBeCloseTo(0.7);
  });

  it("avgConfidence is null when no action has a confidence value", () => {
    const metrics = computeMetrics([{ action_type: "escalate", confidence: null }]);
    expect(metrics.avgConfidence).toBeNull();
  });
});
