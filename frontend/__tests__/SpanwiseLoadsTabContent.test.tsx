/**
 * gh-1002: Tests for the Spanwise Loads tab spinner, empty state, the
 * buildSpanwiseLoadsAnnotationText helper, and the pure Plotly
 * trace/annotation builder (buildSpanwiseLoadsTracesAndAnnotations).
 */
import { describe, it, expect, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import React from "react";
import type {
  SpanwiseLoadsResult,
  SurfaceSpanwiseLoads,
} from "@/hooks/useSpanwiseLoads";

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
    // gh-1008: SparSizingPanel uses these icons
    ChevronDown: icon,
    ChevronRight: icon,
  };
});

// gh-1008: Mock useSparSizing and SparSizingPanel so existing tests don't need
// to deal with the spar-sizing hook and component tree.
vi.mock("@/hooks/useSparSizing", () => ({
  useSparSizing: () => ({
    result: null,
    isRunning: false,
    error: null,
    run: vi.fn(),
  }),
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({ components: [], total: 0, error: null, isLoading: false, mutate: vi.fn() }),
}));

vi.mock("@/components/workbench/SparSizingPanel", () => ({
  SparSizingPanel: () => React.createElement("div", { "data-testid": "spar-sizing-panel-stub" }),
  toSizingParams: () => null,
}));

const plotlyReact = vi.fn().mockResolvedValue(undefined);
const plotlyPurge = vi.fn();
vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: plotlyReact, purge: plotlyPurge },
  react: plotlyReact,
  purge: plotlyPurge,
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

function makeSurface(
  overrides: Partial<SurfaceSpanwiseLoads> = {},
): SurfaceSpanwiseLoads {
  // Two strips, deliberately supplied out of inboard→outboard order so the
  // builder's sort is exercised. y starts at 0.2 (inner) — not the centreline
  // — so the innerX anchoring branch is covered.
  return {
    surface_name: "Main Wing",
    starboard: [
      { y_m: 0.9, chord_m: 0.18, shear_N: 10, bending_moment_Nm: 2 },
      { y_m: 0.2, chord_m: 0.3, shear_N: 80, bending_moment_Nm: 40 },
    ],
    port: [
      { y_m: 0.9, chord_m: 0.18, shear_N: 10, bending_moment_Nm: 2 },
      { y_m: 0.2, chord_m: 0.3, shear_N: 80, bending_moment_Nm: 40 },
    ],
    root_shear_N_starboard: 95.4,
    root_shear_N_port: 95.4,
    root_bending_moment_Nm_starboard: 51.2,
    root_bending_moment_Nm_port: 51.2,
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

  it("mounts the chart and hands traces + layout to Plotly.react when surfaces are present", async () => {
    plotlyReact.mockClear();
    const { SpanwiseLoadsTabContent } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const loads = makeLoads({ surfaces: [makeSurface()] });
    const { queryByTestId, queryByText } = render(
      <SpanwiseLoadsTabContent spanwiseLoadsLoading={false} spanwiseLoads={loads} />,
    );
    expect(queryByTestId("spanwise-loads-spinner")).toBeNull();
    expect(
      queryByText(/Run an analysis to see the spanwise load distribution/),
    ).toBeNull();

    // The chart effect awaits the (mocked) Plotly import then renders the figure.
    await waitFor(() => expect(plotlyReact).toHaveBeenCalledTimes(1));
    const [node, traces, layout] = plotlyReact.mock.calls[0];
    expect(node).toBeInstanceOf(HTMLElement);
    // 2 traces for the single surface (V(y) + M(y)).
    expect(traces).toHaveLength(2);
    // Dual-axis layout with the secondary bending-moment axis.
    expect(layout.yaxis2.overlaying).toBe("y");
    expect(Array.isArray(layout.annotations)).toBe(true);
  });
});

describe("buildSpanwiseLoadsTracesAndAnnotations (gh-1002)", () => {
  it("emits one V(y) and one M(y) trace per surface, full-span sorted", async () => {
    const { buildSpanwiseLoadsTracesAndAnnotations } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const loads = makeLoads({ surfaces: [makeSurface()] });
    const { traces } = buildSpanwiseLoadsTracesAndAnnotations(loads);

    // 2 traces per surface (shear on y, bending on y2).
    expect(traces).toHaveLength(2);
    const [shearTrace, bmTrace] = traces as Array<{
      name: string;
      x: number[];
      y: number[];
      yaxis: string;
    }>;

    expect(shearTrace.name).toBe("V(y) — Main Wing");
    expect(shearTrace.yaxis).toBe("y");
    expect(bmTrace.name).toBe("M(y) — Main Wing");
    expect(bmTrace.yaxis).toBe("y2");

    // Port half mirrored to negative Y, starboard positive — full span,
    // monotonically increasing left→right: [-0.9, -0.2, 0.2, 0.9].
    expect(shearTrace.x).toEqual([-0.9, -0.2, 0.2, 0.9]);
    const sorted = [...shearTrace.x].sort((a, b) => a - b);
    expect(shearTrace.x).toEqual(sorted);

    // Shear values follow the mirrored ordering (inner strip = 80).
    expect(shearTrace.y).toEqual([10, 80, 80, 10]);
    expect(bmTrace.y).toEqual([2, 40, 40, 2]);
  });

  it("anchors root BM/shear annotations at the innermost starboard strip", async () => {
    const { buildSpanwiseLoadsTracesAndAnnotations } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const loads = makeLoads({ surfaces: [makeSurface()] });
    const { annotations } = buildSpanwiseLoadsTracesAndAnnotations(loads);

    // Root BM, Root V, plus the compute-parameter annotation = 3.
    expect(annotations).toHaveLength(3);
    const texts = (annotations as Array<{ text: string }>).map((a) => a.text);
    expect(texts.some((t) => t.includes("Root BM: 51 N·m"))).toBe(true);
    expect(texts.some((t) => t.includes("Root V: 95 N"))).toBe(true);

    const bmAnn = (annotations as Array<{ x: number; yref: string; text: string }>).find(
      (a) => a.text.startsWith("Root BM"),
    )!;
    // innermost starboard strip y = 0.2 (not the centreline)
    expect(bmAnn.x).toBe(0.2);
    expect(bmAnn.yref).toBe("y2");
  });

  it("falls back to x=0 for the root anchor when no starboard strips exist", async () => {
    const { buildSpanwiseLoadsTracesAndAnnotations } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const loads = makeLoads({
      surfaces: [makeSurface({ starboard: [] })],
    });
    const { annotations } = buildSpanwiseLoadsTracesAndAnnotations(loads);
    const bmAnn = (annotations as Array<{ x: number; text: string }>).find((a) =>
      a.text.startsWith("Root BM"),
    )!;
    expect(bmAnn.x).toBe(0.0);
  });

  it("emits no traces and only the compute annotation when there are no surfaces", async () => {
    const { buildSpanwiseLoadsTracesAndAnnotations } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const { traces, annotations } = buildSpanwiseLoadsTracesAndAnnotations(
      makeLoads(),
    );
    expect(traces).toHaveLength(0);
    // Only the compute-parameter annotation (no main surface → no root arrows).
    expect(annotations).toHaveLength(1);
    expect((annotations[0] as { xref: string }).xref).toBe("paper");
  });

  it("includes the compute-parameter annotation text from buildSpanwiseLoadsAnnotationText", async () => {
    const { buildSpanwiseLoadsTracesAndAnnotations, buildSpanwiseLoadsAnnotationText } =
      await import("@/components/workbench/AnalysisViewerPanel");
    const loads = makeLoads({ surfaces: [makeSurface()] });
    const { annotations } = buildSpanwiseLoadsTracesAndAnnotations(loads);
    const computeAnn = (annotations as Array<{ xref: string; text: string }>).find(
      (a) => a.xref === "paper",
    )!;
    expect(computeAnn.text).toBe(buildSpanwiseLoadsAnnotationText(loads));
  });
});
