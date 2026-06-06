/**
 * gh-870: characteristic key-points marked as visible Plotly markers on
 * Analysis-Polar charts (CL-α and L/D-α).
 *
 * Tests the pure builder function `buildAnalysisPolarMarkerTrace`, which
 * returns a scatter trace with the expected x (degrees), y, and text label
 * for a given chart id + derived polar data.
 */
import { describe, it, expect, vi } from "vitest";

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

import { buildAnalysisPolarMarkerTrace } from "@/components/workbench/AnalysisViewerPanel";

// ---------------------------------------------------------------------------
// Helper: a PolarCharts-like object
// ---------------------------------------------------------------------------
function makePolar({
  clMax = 1.2,
  alphaClMax = 10,
  ldMax = 20,
  alphaLdMax = 5,
}: {
  clMax?: number | null;
  alphaClMax?: number | null;
  ldMax?: number | null;
  alphaLdMax?: number | null;
} = {}) {
  return { clMax, alphaClMax, ldMax, alphaLdMax };
}

// ---------------------------------------------------------------------------
// CL-α chart ("cl")
// ---------------------------------------------------------------------------
describe("buildAnalysisPolarMarkerTrace – cl chart", () => {
  it("returns a trace with the CL_max marker at the correct alpha (degrees)", () => {
    const polar = makePolar({ clMax: 1.2, alphaClMax: 10 });
    const trace = buildAnalysisPolarMarkerTrace("cl", polar);
    expect(trace).not.toBeNull();
    expect(trace!.x).toEqual([10]);
    expect(trace!.y).toEqual([1.2]);
    expect(trace!.text[0]).toMatch(/CL,max/i);
  });

  it("returns null when clMax is null", () => {
    const polar = makePolar({ clMax: null, alphaClMax: 10 });
    expect(buildAnalysisPolarMarkerTrace("cl", polar)).toBeNull();
  });

  it("returns null when alphaClMax is null", () => {
    const polar = makePolar({ clMax: 1.2, alphaClMax: null });
    expect(buildAnalysisPolarMarkerTrace("cl", polar)).toBeNull();
  });

  it("returns null when clMax is non-finite", () => {
    const polar = makePolar({ clMax: NaN, alphaClMax: 10 });
    expect(buildAnalysisPolarMarkerTrace("cl", polar)).toBeNull();
  });

  it("returns null when alphaClMax is non-finite", () => {
    const polar = makePolar({ clMax: 1.2, alphaClMax: Infinity });
    expect(buildAnalysisPolarMarkerTrace("cl", polar)).toBeNull();
  });

  it("marker uses the dark-theme style (white, circle, size 7)", () => {
    const trace = buildAnalysisPolarMarkerTrace("cl", makePolar());
    expect(trace!.marker.color).toBe("#FAFAFA");
    expect(trace!.marker.symbol).toBe("circle");
    expect(trace!.marker.size).toBe(7);
    expect(trace!.textfont.color).toBe("#FAFAFA");
    expect(trace!.mode).toBe("markers+text");
    expect(trace!.textposition).toBe("top center");
  });
});

// ---------------------------------------------------------------------------
// L/D-α chart ("ld")
// ---------------------------------------------------------------------------
describe("buildAnalysisPolarMarkerTrace – ld chart", () => {
  it("returns a trace with the (L/D)_max marker at the correct alpha (degrees)", () => {
    const polar = makePolar({ ldMax: 20, alphaLdMax: 5 });
    const trace = buildAnalysisPolarMarkerTrace("ld", polar);
    expect(trace).not.toBeNull();
    expect(trace!.x).toEqual([5]);
    expect(trace!.y).toEqual([20]);
    expect(trace!.text[0]).toMatch(/L\/D,max/i);
  });

  it("returns null when ldMax is null", () => {
    const polar = makePolar({ ldMax: null, alphaLdMax: 5 });
    expect(buildAnalysisPolarMarkerTrace("ld", polar)).toBeNull();
  });

  it("returns null when alphaLdMax is null", () => {
    const polar = makePolar({ ldMax: 20, alphaLdMax: null });
    expect(buildAnalysisPolarMarkerTrace("ld", polar)).toBeNull();
  });

  it("returns null when ldMax is non-finite", () => {
    const polar = makePolar({ ldMax: Infinity, alphaLdMax: 5 });
    expect(buildAnalysisPolarMarkerTrace("ld", polar)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Unknown / unsupported chart IDs
// ---------------------------------------------------------------------------
describe("buildAnalysisPolarMarkerTrace – unsupported chart ids", () => {
  it("returns null for 'cd' (no characteristic point defined)", () => {
    expect(buildAnalysisPolarMarkerTrace("cd", makePolar())).toBeNull();
  });

  it("returns null for 'polar' (drag polar — no alpha axis)", () => {
    expect(buildAnalysisPolarMarkerTrace("polar", makePolar())).toBeNull();
  });

  it("returns null for 'cm'", () => {
    expect(buildAnalysisPolarMarkerTrace("cm", makePolar())).toBeNull();
  });
});
