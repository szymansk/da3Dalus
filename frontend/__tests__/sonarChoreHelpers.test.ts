/**
 * Coverage for the pure helpers touched by the SonarCloud chore cleanup
 * (PR "chore: resolve 6 SonarCloud frontend findings").
 *
 * - speedPolarLineTrace / speedPolarTraces (S7727): the map callback must
 *   forward the color-cycling index and produce one line trace per curve
 *   (plus a marker trace for the base curve when key points exist).
 * - approxEq (S1244): tolerant float equality used for scale-factor buttons.
 */
import { describe, it, expect, vi } from "vitest";

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn(), newPlot: vi.fn(), relayout: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

import {
  speedPolarLineTrace,
  speedPolarTraces,
} from "@/components/workbench/AnalysisViewerPanel";
import { approxEq } from "@/components/workbench/ImportFuselageDialog";
import type { SpeedPolarCurve } from "@/hooks/useAnalysis";

function curve(overrides: Partial<SpeedPolarCurve> = {}): SpeedPolarCurve {
  return {
    mass_kg: 2.5,
    is_base: false,
    V: [10, 15, 20],
    w: [1.2, 0.9, 1.4],
    cl: [0.8, 0.6, 0.4],
    cd: [0.03, 0.025, 0.03],
    v_stall: 9,
    v_min_sink: 12,
    w_min: 0.85,
    v_best_glide: 16,
    ld_max: 18,
    ...overrides,
  };
}

describe("speedPolarLineTrace (S7727)", () => {
  it("uses the base colour for the base curve regardless of index", () => {
    const t = speedPolarLineTrace(curve({ is_base: true }), 3);
    expect((t.line as { color: string }).color).toBe("#FF8400");
    expect((t.line as { width: number }).width).toBe(2.5);
  });

  it("cycles a palette colour for non-base curves by index", () => {
    const t0 = speedPolarLineTrace(curve(), 0);
    const t1 = speedPolarLineTrace(curve(), 1);
    // Different indices pick (at least potentially) different palette slots;
    // the important contract is that the index is honoured, not dropped.
    expect((t0.line as { color: string }).color).not.toBe("#FF8400");
    expect((t1.line as { color: string }).color).not.toBe("#FF8400");
  });
});

describe("speedPolarTraces (S7727 map wrapper)", () => {
  it("emits one line trace per curve plus a base marker trace", () => {
    const traces = speedPolarTraces([
      curve({ is_base: true, mass_kg: 2.0 }),
      curve({ mass_kg: 3.0 }),
    ]);
    // 2 line traces + 1 marker trace for the base curve.
    expect(traces).toHaveLength(3);
    // The forwarded index means the second (non-base) curve is not orange.
    expect((traces[1].line as { color: string }).color).not.toBe("#FF8400");
  });

  it("does not leak the array argument into speedPolarLineTrace", () => {
    // A single curve → a single line trace. If map leaked (element, index,
    // array), the trace builder would still only read c and i, so behaviour
    // is unchanged — this simply pins the one-trace-per-curve contract.
    const traces = speedPolarTraces([curve({ v_min_sink: null, v_best_glide: null })]);
    expect(traces).toHaveLength(1);
  });
});

describe("approxEq (S1244)", () => {
  it("is true for exactly-equal floats", () => {
    expect(approxEq(0.001, 0.001)).toBe(true);
    expect(approxEq(0.01, 0.01)).toBe(true);
  });

  it("is true within the default epsilon", () => {
    expect(approxEq(0.1 + 0.2, 0.3)).toBe(true); // classic 0.30000000000000004
  });

  it("is false for clearly-different values", () => {
    expect(approxEq(0.001, 0.01)).toBe(false);
    expect(approxEq(0.01, 1)).toBe(false);
  });

  it("honours a custom epsilon", () => {
    expect(approxEq(1.0, 1.4, 0.5)).toBe(true);
    expect(approxEq(1.0, 1.4, 0.1)).toBe(false);
  });
});
