/**
 * Unit tests for PerformanceOverview KPI cards (gh-521 regression).
 *
 * Ensures that KpiCard renders for every backend confidence literal
 * including the 'computed' tier introduced in gh-475/#480. Prevents
 * frontend/backend type drift that caused TypeError on style.bg.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PerformanceOverview } from "@/components/workbench/PerformanceOverview";
import type { PerformanceKPI } from "@/hooks/useFlightEnvelope";

const ALL_CONFIDENCE_VALUES: PerformanceKPI["confidence"][] = [
  "trimmed",
  "computed",
  "estimated",
  "limit",
];

function makeKpi(
  confidence: PerformanceKPI["confidence"],
  label: string,
): PerformanceKPI {
  return {
    label,
    display_name: label.toUpperCase(),
    value: 12.5,
    unit: "m/s",
    source_op_id: null,
    confidence,
  };
}

describe("PerformanceOverview (gh-521)", () => {
  it("renders each backend confidence tier without crashing", () => {
    const kpis = ALL_CONFIDENCE_VALUES.map((c) => makeKpi(c, `v_${c}`));
    render(<PerformanceOverview kpis={kpis} />);
    for (const c of ALL_CONFIDENCE_VALUES) {
      expect(screen.getByText(`V_${c.toUpperCase()}`)).toBeDefined();
    }
  });

  it("renders 'Computed' badge for polar-derived KPIs (gh-475)", () => {
    const kpi = makeKpi("computed", "v_md");
    render(<PerformanceOverview kpis={[kpi]} />);
    expect(screen.getByText(/Computed/)).toBeDefined();
  });

  it("shows empty-state when no KPIs", () => {
    render(<PerformanceOverview kpis={[]} />);
    expect(screen.getByText(/No performance data available/)).toBeDefined();
  });
});
