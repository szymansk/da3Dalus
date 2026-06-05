/**
 * Unit tests for the 2D airfoil proxy chart data helpers (gh-841).
 *
 * Tests cover:
 * - buildAirfoilProxyChartData: filtering, formula correctness, sort order
 * - findPeakClOverCd / findPeakCl15OverCd: peak detection
 */

import { describe, it, expect } from "vitest";
import {
  buildAirfoilProxyChartData,
  findPeakClOverCd,
  findPeakCl15OverCd,
} from "@/lib/airfoilProxyChartData";

// ---------------------------------------------------------------------------
// buildAirfoilProxyChartData
// ---------------------------------------------------------------------------

describe("buildAirfoilProxyChartData", () => {
  it("computes cl/cd correctly", () => {
    const data = buildAirfoilProxyChartData([0.8], [0.02]);
    expect(data).toHaveLength(1);
    expect(data[0].clOverCd).toBeCloseTo(0.8 / 0.02, 6);
  });

  it("computes cl^1.5/cd correctly", () => {
    const data = buildAirfoilProxyChartData([0.8], [0.02]);
    expect(data[0].cl15OverCd).toBeCloseTo(Math.pow(0.8, 1.5) / 0.02, 6);
  });

  it("filters out null values", () => {
    const data = buildAirfoilProxyChartData([null, 0.8, null], [0.02, 0.02, 0.02]);
    expect(data).toHaveLength(1);
    expect(data[0].cl).toBe(0.8);
  });

  it("filters out non-positive cd", () => {
    const data = buildAirfoilProxyChartData([0.8, 0.9], [0.0, 0.02]);
    expect(data).toHaveLength(1);
    expect(data[0].cl).toBe(0.9);
  });

  it("filters out non-positive cl (no endurance metric for cl <= 0)", () => {
    const data = buildAirfoilProxyChartData([-0.1, 0.0, 0.5], [0.02, 0.02, 0.02]);
    expect(data).toHaveLength(1);
    expect(data[0].cl).toBe(0.5);
  });

  it("filters out non-finite values", () => {
    const data = buildAirfoilProxyChartData(
      [Infinity, NaN, 0.7],
      [0.02, 0.02, 0.02],
    );
    expect(data).toHaveLength(1);
  });

  it("returns empty array for all-null inputs", () => {
    const data = buildAirfoilProxyChartData([null, null], [null, null]);
    expect(data).toHaveLength(0);
  });

  it("returns empty array for empty inputs", () => {
    expect(buildAirfoilProxyChartData([], [])).toHaveLength(0);
  });

  it("sorts output by cl ascending", () => {
    const data = buildAirfoilProxyChartData(
      [1.5, 0.5, 1.0],
      [0.03, 0.02, 0.025],
    );
    const cls = data.map((p) => p.cl);
    for (let i = 1; i < cls.length; i++) {
      expect(cls[i]).toBeGreaterThanOrEqual(cls[i - 1]);
    }
  });

  it("handles mismatched array lengths gracefully (uses shorter)", () => {
    const data = buildAirfoilProxyChartData([0.5, 0.8, 1.0], [0.02, 0.025]);
    expect(data.length).toBeLessThanOrEqual(2);
  });

  it("cl value is preserved in output", () => {
    const data = buildAirfoilProxyChartData([0.9], [0.03]);
    expect(data[0].cl).toBe(0.9);
  });
});

// ---------------------------------------------------------------------------
// findPeakClOverCd
// ---------------------------------------------------------------------------

describe("findPeakClOverCd", () => {
  it("returns null for empty data", () => {
    expect(findPeakClOverCd([])).toBeNull();
  });

  it("finds the correct peak", () => {
    const data = buildAirfoilProxyChartData(
      [0.5, 1.0, 0.8],
      [0.02, 0.025, 0.015], // cl/cd: 25, 40, 53.3
    );
    const peak = findPeakClOverCd(data);
    expect(peak).not.toBeNull();
    expect(peak!.cl).toBe(0.8); // highest cl/cd = 0.8/0.015
  });
});

// ---------------------------------------------------------------------------
// findPeakCl15OverCd
// ---------------------------------------------------------------------------

describe("findPeakCl15OverCd", () => {
  it("returns null for empty data", () => {
    expect(findPeakCl15OverCd([])).toBeNull();
  });

  it("finds the correct peak", () => {
    const data = buildAirfoilProxyChartData(
      [0.5, 1.0, 0.8],
      [0.02, 0.025, 0.03],
    );
    // cl^1.5/cd: 0.5^1.5/0.02=17.7, 1.0^1.5/0.025=40, 0.8^1.5/0.03=23.9
    const peak = findPeakCl15OverCd(data);
    expect(peak).not.toBeNull();
    expect(peak!.cl).toBe(1.0);
  });
});
