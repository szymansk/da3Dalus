/**
 * gh-817: the analysis Polar tab crashed with
 *   "undefined is not an object (evaluating 'charts.clMax.toFixed')"
 * once the backend (gh-815) started serializing non-finite aero coefficients
 * as JSON null. `Math.max(...CL)` coerces null -> 0, so `CL.indexOf(max)`
 * returns -1 (e.g. all-null, or all-negative CL plus a null), and `CL[-1]`
 * is undefined -> `.toFixed` throws.
 *
 * These tests cover the null-safe extraction helpers.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import {
  finiteArgMax,
  safeToFixed,
  derivePolarCharts,
  polarHasFiniteData,
} from "@/components/workbench/AnalysisViewerPanel";
import type { AnalysisResult } from "@/hooks/useAnalysis";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
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
    MapPin: icon,
  };
});
vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: () => ({ data: null, isLoading: false }),
}));
vi.mock("@/hooks/useDesignAssumptions", () => ({
  useDesignAssumptions: () => ({ data: null, isLoading: false }),
}));

describe("finiteArgMax", () => {
  it("returns the index of the largest finite value", () => {
    expect(finiteArgMax([0.1, 0.5, 0.3])).toBe(1);
  });

  it("ignores null / undefined / NaN entries", () => {
    expect(finiteArgMax([null, 0.5, undefined])).toBe(1);
    expect(finiteArgMax([0.1, NaN, 0.3])).toBe(2);
  });

  it("handles all-negative arrays without being fooled by null->0 coercion", () => {
    // the exact crash case: Math.max(...[-0.2, null, -0.1]) === 0, indexOf === -1
    expect(finiteArgMax([-0.2, null, -0.1])).toBe(2);
  });

  it("returns -1 when there is no finite value", () => {
    expect(finiteArgMax([null, null, null])).toBe(-1);
    expect(finiteArgMax([])).toBe(-1);
  });
});

describe("safeToFixed", () => {
  it("formats finite numbers, including zero", () => {
    expect(safeToFixed(1.234, 2)).toBe("1.23");
    expect(safeToFixed(0, 2)).toBe("0.00");
  });

  it("returns the fallback for null / undefined / NaN", () => {
    expect(safeToFixed(null, 2)).toBe("n/a");
    expect(safeToFixed(undefined, 2)).toBe("n/a");
    expect(safeToFixed(Number.NaN, 2)).toBe("n/a");
  });
});

const base = (over: Partial<AnalysisResult>): AnalysisResult => ({
  CL: [],
  CD: [],
  Cm: [],
  alpha: [],
  ...over,
});

describe("derivePolarCharts", () => {
  it("returns null when there is no data", () => {
    expect(derivePolarCharts(null)).toBeNull();
    expect(derivePolarCharts(base({ CL: [] }))).toBeNull();
  });

  it("computes characteristic points for a normal sweep", () => {
    const charts = derivePolarCharts(
      base({ CL: [0.1, 0.8, 0.5], CD: [0.01, 0.04, 0.03], Cm: [0, -0.1, -0.2], alpha: [0, 5, 10] }),
    );
    expect(charts).not.toBeNull();
    expect(charts!.clMax).toBe(0.8);
    expect(charts!.alphaClMax).toBe(5);
  });

  it("does not crash on an all-null (degenerate) sweep — the gh-817 regression", () => {
    const charts = derivePolarCharts(
      base({ CL: [null, null], CD: [null, null], Cm: [], alpha: [0, 5] }),
    );
    expect(charts).not.toBeNull();
    expect(charts!.clMax).toBeNull();
    expect(charts!.alphaClMax).toBeNull();
    expect(charts!.ldMax).toBeNull();
    expect(charts!.alphaLdMax).toBeNull();
    // and the annotation it feeds renders a fallback, not a thrown TypeError
    expect(safeToFixed(charts!.clMax, 2)).toBe("n/a");
  });

  it("treats zero drag as a non-computable L/D (null, not 0)", () => {
    const charts = derivePolarCharts(
      base({ CL: [0.5, 0.7], CD: [0, 0.05], Cm: [], alpha: [0, 5] }),
    );
    // cd === 0 -> null (gap), so it is never selected as the L/D max
    expect(charts!.clOverCd[0]).toBeNull();
    expect(charts!.clOverCd[1]).toBeCloseTo(0.7 / 0.05);
    expect(charts!.ldMax).toBeCloseTo(0.7 / 0.05);
    expect(charts!.alphaLdMax).toBe(5);
  });

  it("still reports a finite max when only some entries are null", () => {
    const charts = derivePolarCharts(
      base({ CL: [null, 0.9, null], CD: [null, 0.05, null], Cm: [], alpha: [0, 6, 12] }),
    );
    expect(charts!.clMax).toBe(0.9);
    expect(charts!.alphaClMax).toBe(6);
  });
});

describe("polarHasFiniteData", () => {
  it("is false when every coefficient is null", () => {
    const charts = derivePolarCharts(
      base({ CL: [null, null], CD: [null, null], Cm: [], alpha: [0, 5] }),
    );
    expect(polarHasFiniteData(charts!)).toBe(false);
  });

  it("is true for a normal sweep", () => {
    const charts = derivePolarCharts(
      base({ CL: [0.1, 0.8], CD: [0.01, 0.04], Cm: [0, -0.1], alpha: [0, 5] }),
    );
    expect(polarHasFiniteData(charts!)).toBe(true);
  });

  it("is true when only some series have finite values", () => {
    const charts = derivePolarCharts(
      base({ CL: [null, null], CD: [0.02, 0.03], Cm: [], alpha: [0, 5] }),
    );
    expect(polarHasFiniteData(charts!)).toBe(true);
  });
});

describe("Polar tab empty states", () => {
  const renderPolar = async (result: AnalysisResult | null) => {
    const { AnalysisViewerPanel } = await import("@/components/workbench/AnalysisViewerPanel");
    render(
      <AnalysisViewerPanel
        result={result}
        activeTab="Polar"
        onTabChange={() => {}}
        hasWings
        wingXSecs={null}
      />,
    );
  };

  it("shows a 'no valid results' notice for an all-null sweep instead of blank charts", async () => {
    await renderPolar({ CL: [null, null], CD: [null, null], Cm: [], alpha: [0, 5] });
    expect(screen.getByText(/no valid results/i)).toBeInTheDocument();
    expect(screen.queryByText(/run an analysis/i)).not.toBeInTheDocument();
  });

  it("shows the run-analysis prompt when there is no result yet", async () => {
    await renderPolar(null);
    expect(screen.getByText(/run an analysis/i)).toBeInTheDocument();
    expect(screen.queryByText(/no valid results/i)).not.toBeInTheDocument();
  });
});
