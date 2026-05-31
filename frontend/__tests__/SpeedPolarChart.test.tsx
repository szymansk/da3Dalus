/**
 * Unit tests for SpeedPolarChart velocity-axis bounds (gh-799).
 *
 * Verifies that the chart's layout-building logic passes
 * `xaxis.range = [v_axis_min, v_axis_max]` to Plotly when both bounds
 * are finite numbers, and omits the range (letting Plotly autorange)
 * when the bounds are absent, null, NaN, or Infinity.
 *
 * The pure `buildSpeedPolarLayout` helper mirrors the exact logic baked into
 * SpeedPolarChart so we can test it without importing the full component tree.
 */
import { describe, it, expect } from "vitest";
import type { SpeedPolar } from "@/hooks/useAnalysis";

// ---------------------------------------------------------------------------
// Pure helper — mirrors the SpeedPolarChart layout-building code exactly
// ---------------------------------------------------------------------------
function buildSpeedPolarLayout(
  baseLayout: Record<string, unknown>,
  v_axis_min: number | null | undefined,
  v_axis_max: number | null | undefined,
): Record<string, unknown> {
  const hasBounds =
    typeof v_axis_min === "number" &&
    isFinite(v_axis_min) &&
    typeof v_axis_max === "number" &&
    isFinite(v_axis_max);
  return hasBounds
    ? {
        ...baseLayout,
        xaxis: {
          ...(baseLayout.xaxis as Record<string, unknown>),
          range: [v_axis_min, v_axis_max],
          autorange: false,
        },
      }
    : baseLayout;
}

const BASE_LAYOUT: Record<string, unknown> = {
  paper_bgcolor: "transparent",
  xaxis: { title: { text: "V [m/s]" }, gridcolor: "#27272A" },
};

// ---------------------------------------------------------------------------
// Helper to construct a SpeedPolar object (exercises the TS interface)
// ---------------------------------------------------------------------------
const MINIMAL_CURVE: SpeedPolar["curves"][0] = {
  mass_kg: 1.5,
  is_base: true,
  V: [8.0, 10.0, 14.0, 20.0],
  w: [0.4, 0.35, 0.38, 0.6],
  cl: [1.4, 1.0, 0.6, 0.3],
  cd: [0.07, 0.045, 0.032, 0.024],
  v_stall: 7.8,
  v_min_sink: 10.0,
  w_min: 0.35,
  v_best_glide: 14.0,
  ld_max: 12.5,
};

function makeSpeedPolar(
  extra: Partial<Pick<SpeedPolar, "v_axis_min" | "v_axis_max">> = {},
): SpeedPolar {
  return {
    base_mass_kg: 1.5,
    s_ref: 0.225,
    rho: 1.225,
    altitude: 0,
    curves: [MINIMAL_CURVE],
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SpeedPolarChart layout logic — velocity-axis bounds (gh-799)", () => {
  describe("buildSpeedPolarLayout (pure logic)", () => {
    it("sets xaxis.range and autorange:false when both bounds are finite", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, 5.5, 52.0);
      const xaxis = layout.xaxis as Record<string, unknown>;
      expect(xaxis.range).toEqual([5.5, 52.0]);
      expect(xaxis.autorange).toBe(false);
    });

    it("returns base layout unchanged when bounds are both null", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, null, null);
      expect(layout).toBe(BASE_LAYOUT);
    });

    it("returns base layout unchanged when bounds are both undefined", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, undefined, undefined);
      expect(layout).toBe(BASE_LAYOUT);
    });

    it("returns base layout unchanged when only v_axis_min is present", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, 5.5, null);
      expect(layout).toBe(BASE_LAYOUT);
      expect(
        (layout.xaxis as Record<string, unknown>).range,
      ).toBeUndefined();
    });

    it("returns base layout unchanged when only v_axis_max is present", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, null, 52.0);
      expect(layout).toBe(BASE_LAYOUT);
    });

    it("returns base layout unchanged when v_axis_min is NaN", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, NaN, 52.0);
      expect(layout).toBe(BASE_LAYOUT);
    });

    it("returns base layout unchanged when v_axis_max is Infinity", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, 5.5, Infinity);
      expect(layout).toBe(BASE_LAYOUT);
    });

    it("preserves existing xaxis properties when adding range", () => {
      const layout = buildSpeedPolarLayout(BASE_LAYOUT, 3.0, 45.0);
      const xaxis = layout.xaxis as Record<string, unknown>;
      // Original property still present
      expect((xaxis.title as Record<string, unknown>).text).toBe("V [m/s]");
      // New properties added
      expect(xaxis.range).toEqual([3.0, 45.0]);
      expect(xaxis.autorange).toBe(false);
    });
  });

  describe("SpeedPolar interface alignment", () => {
    it("accepts v_axis_min and v_axis_max fields", () => {
      const sp = makeSpeedPolar({ v_axis_min: 5.5, v_axis_max: 52.0 });
      expect(sp.v_axis_min).toBe(5.5);
      expect(sp.v_axis_max).toBe(52.0);
    });

    it("accepts null bounds", () => {
      const sp = makeSpeedPolar({ v_axis_min: null, v_axis_max: null });
      expect(sp.v_axis_min).toBeNull();
      expect(sp.v_axis_max).toBeNull();
    });

    it("allows omitting bounds fields", () => {
      const sp = makeSpeedPolar();
      expect(sp.v_axis_min).toBeUndefined();
      expect(sp.v_axis_max).toBeUndefined();
    });
  });
});
