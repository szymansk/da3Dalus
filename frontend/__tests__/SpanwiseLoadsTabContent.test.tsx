/**
 * gh-1002: Tests for the Spanwise Loads tab spinner, empty state,
 * and the buildSpanwiseLoadsAnnotationText helper.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import type { SpanwiseLoadsResult } from "@/hooks/useSpanwiseLoads";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": "lucide-icon" });
  return {
    Maximize2: icon,
    Minimize2: icon,
    Settings: icon,
    Wind: icon,
    Ruler: icon,
    Target: icon,
    Navigation: icon,
    Gauge: icon,
    AlertTriangle: icon,
    SlidersHorizontal: icon,
    Activity: icon,
    Loader2: icon,
    Plane: icon,
    TrendingUp: icon,
    Zap: icon,
    RefreshCw: icon,
    Square: icon,
    ArrowLeftRight: icon,
  };
});

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

function makeLoads(overrides: Partial<SpanwiseLoadsResult> = {}): SpanwiseLoadsResult {
  return {
    alpha: 2.0,
    velocity_mps: 30.0,
    altitude_m: 0.0,
    dynamic_pressure_Pa: 551.25,
    surfaces: [],
    ...overrides,
  };
}

describe("buildSpanwiseLoadsAnnotationText (gh-1002)", () => {
  it("includes alpha, velocity, altitude, and q", async () => {
    const { buildSpanwiseLoadsAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildSpanwiseLoadsAnnotationText(makeLoads());
    expect(text).toContain("α = 2.00°");
    expect(text).toContain("V = 30.0 m/s");
    expect(text).toContain("Alt = 0 m");
    expect(text).toContain("q = 551.3 Pa");
  });

  it("produces two <br>-separated lines", async () => {
    const { buildSpanwiseLoadsAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildSpanwiseLoadsAnnotationText(makeLoads());
    expect(text.split("<br>")).toHaveLength(2);
  });
});

describe("SpanwiseLoadsTabContent loading state (gh-1002)", () => {
  it("renders the spinner when loading", async () => {
    const { SpanwiseLoadsTabContent } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const { getByTestId, getByText } = render(
      <SpanwiseLoadsTabContent spanwiseLoadsLoading={true} spanwiseLoads={null} />,
    );
    const spinner = getByTestId("spanwise-loads-spinner");
    expect(spinner).not.toBeNull();
    expect(spinner.querySelector('[data-testid="lucide-icon"]')).not.toBeNull();
    expect(getByText(/Computing spanwise loads/)).not.toBeNull();
  });

  it("renders empty state when not loading and no data", async () => {
    const { SpanwiseLoadsTabContent } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const { queryByTestId, getByText } = render(
      <SpanwiseLoadsTabContent spanwiseLoadsLoading={false} spanwiseLoads={null} />,
    );
    expect(queryByTestId("spanwise-loads-spinner")).toBeNull();
    expect(getByText(/Run an analysis to see the spanwise load distribution/)).not.toBeNull();
  });
});
