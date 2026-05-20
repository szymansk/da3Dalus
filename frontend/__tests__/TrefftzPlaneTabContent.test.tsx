/**
 * gh-592: tests for the Trefftz-Plane spinner + compute-parameter annotation.
 *
 * Covers the two coordinated UX changes:
 *  1. Loading state renders a Loader2 spinner (not the old plain text).
 *  2. `buildTrefftzAnnotationText` produces a 4-line, structured readout
 *     containing every echoed compute parameter.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import type { StripForcesResult } from "@/hooks/useStripForces";

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

// Some descendant components of AnalysisViewerPanel may import the dynamic
// Plotly bundle at module load. We don't render TrefftzPlaneChart in these
// tests (only the loading / empty branches and the annotation helper), but a
// defensive mock keeps the test environment hermetic.
vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

function makeStripForces(overrides: Partial<StripForcesResult> = {}): StripForcesResult {
  return {
    alpha: 2.5,
    beta: 0.0,
    mach: 0.044,
    sref: 0.6,
    cref: 0.25,
    bref: 2.4,
    surfaces: [],
    velocity_mps: 15.0,
    altitude_m: 500,
    xyz_ref_m: [0.25, 0.0, 0.0],
    wing_name: "main_wing",
    reynolds: 5.1e5,
    aero_model: "AVL",
    computed_at: "2026-05-19T14:07:00Z",
    operating_point_label: "level_cruise",
    ...overrides,
  };
}

describe("buildTrefftzAnnotationText (gh-592)", () => {
  it("emits four <br>-separated lines", async () => {
    const { buildTrefftzAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildTrefftzAnnotationText(makeStripForces());
    expect(text.split("<br>")).toHaveLength(4);
  });

  it("includes flow / geometry / reference / run sections", async () => {
    const { buildTrefftzAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildTrefftzAnnotationText(makeStripForces());
    expect(text).toMatch(/Flow/);
    expect(text).toMatch(/Geometry/);
    expect(text).toMatch(/Reference/);
    expect(text).toMatch(/Run/);
  });

  it("renders every echoed compute parameter", async () => {
    const { buildTrefftzAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildTrefftzAnnotationText(makeStripForces());
    // Flow line
    expect(text).toContain("α = 2.50°");
    expect(text).toContain("β = 0.00°");
    expect(text).toContain("V = 15.0 m/s");
    expect(text).toContain("Mach = 0.044");
    expect(text).toContain("Alt = 500 m");
    // Geometry line
    expect(text).toContain("Wing: main_wing");
    expect(text).toContain("S_ref = 0.6000 m²");
    expect(text).toContain("C_ref = 0.2500 m");
    expect(text).toContain("B_ref = 2.4000 m");
    // Reference line
    expect(text).toContain("x_cg = (0.250, 0.000, 0.000) m");
    expect(text).toContain("Re = 5.10e+5");
    expect(text).toContain("Model: AVL");
    // Run line
    expect(text).toContain("2026-05-19T14:07:00Z");
    expect(text).toContain("OP: level_cruise");
  });

  it("falls back to em-dash for missing fields", async () => {
    const { buildTrefftzAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const partial: StripForcesResult = {
      alpha: 0,
      beta: 0,
      mach: 0,
      sref: 0,
      cref: 0,
      bref: 0,
      surfaces: [],
    };
    const text = buildTrefftzAnnotationText(partial);
    // Wing name + computed_at fall back to em-dash
    expect(text).toContain("Wing: —");
    expect(text).toMatch(/Run\s+—/);
    // xyz_ref_m missing falls back to em-dash
    expect(text).toContain("x_cg = —");
    // OP label section absent
    expect(text).not.toContain("OP:");
  });

  it("omits the OP-label suffix when operating_point_label is null", async () => {
    const { buildTrefftzAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildTrefftzAnnotationText(
      makeStripForces({ operating_point_label: null })
    );
    expect(text).not.toContain("OP:");
  });

  it("uses AVL as the default aero model when missing", async () => {
    const { buildTrefftzAnnotationText } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const text = buildTrefftzAnnotationText(
      makeStripForces({ aero_model: undefined })
    );
    expect(text).toContain("Model: AVL");
  });
});

describe("TrefftzPlaneTabContent loading state (gh-592)", () => {
  it("renders the Loader2 spinner under the data-testid hook when loading", async () => {
    const { TrefftzPlaneTabContent } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const { getByTestId, getByText } = render(
      <TrefftzPlaneTabContent stripForcesLoading={true} stripForces={null} />,
    );
    const spinner = getByTestId("trefftz-spinner");
    expect(spinner).not.toBeNull();
    // The Loader2 icon (mocked above with data-testid="lucide-icon") lives
    // inside the spinner container.
    expect(spinner.querySelector('[data-testid="lucide-icon"]')).not.toBeNull();
    expect(getByText(/Running strip-force analysis/)).not.toBeNull();
  });

  it("renders empty-state copy when not loading and no surfaces", async () => {
    const { TrefftzPlaneTabContent } = await import(
      "@/components/workbench/AnalysisViewerPanel"
    );
    const { queryByTestId, getByText } = render(
      <TrefftzPlaneTabContent stripForcesLoading={false} stripForces={null} />,
    );
    expect(queryByTestId("trefftz-spinner")).toBeNull();
    expect(getByText(/Run an analysis to see strip-force distributions/)).not.toBeNull();
  });
});
