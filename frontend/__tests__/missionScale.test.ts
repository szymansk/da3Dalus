import { describe, it, expect } from "vitest";
import {
  AXIS_UNITS,
  computeAxisRanges,
  normalizedToRaw,
} from "@/lib/missionScale";
import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";
import type { MissionKpiSet, MissionAxisKpi } from "@/hooks/useMissionKpis";

const trainer: MissionPreset = {
  id: "trainer",
  label: "Trainer",
  description: "",
  target_polygon: {
    stall_safety: 1,
    glide: 0.4,
    climb: 0.3,
    cruise: 0.3,
    maneuver: 0.3,
    wing_loading: 0.3,
    field_friendliness: 0.9,
  },
  axis_ranges: {
    stall_safety: [1.3, 2.5],
    glide: [5, 18],
    climb: [5, 25],
    cruise: [10, 25],
    maneuver: [2, 5],
    wing_loading: [20, 80],
    field_friendliness: [3, 100],
  },
  suggested_estimates: {
    g_limit: 3,
    target_static_margin: 0.15,
    cl_max: 1.4,
    power_to_weight: 0.5,
    prop_efficiency: 0.7,
  },
};

const sailplane: MissionPreset = {
  ...trainer,
  id: "sailplane",
  axis_ranges: {
    stall_safety: [1.3, 2.0],
    glide: [15, 35],
    climb: [15, 60],
    cruise: [10, 25],
    maneuver: [2.5, 5.5],
    wing_loading: [10, 50],
    field_friendliness: [3, 100],
  },
};

describe("computeAxisRanges", () => {
  it("uses single mission range when only one is active", () => {
    const ranges = computeAxisRanges([trainer]);
    expect(ranges.glide).toEqual([5, 18]);
  });

  it("returns [min(mins), max(maxes)] over active missions", () => {
    const ranges = computeAxisRanges([trainer, sailplane]);
    expect(ranges.glide).toEqual([5, 35]);
    expect(ranges.stall_safety).toEqual([1.3, 2.5]);
    expect(ranges.wing_loading).toEqual([10, 80]);
  });
});

describe("normalizedToRaw (gh-601)", () => {
  it("maps 0 to range minimum", () => {
    expect(normalizedToRaw(0, [10, 25])).toBeCloseTo(10);
  });

  it("maps 1 to range maximum", () => {
    expect(normalizedToRaw(1, [10, 25])).toBeCloseTo(25);
  });

  it("interpolates linearly inside the range", () => {
    expect(normalizedToRaw(0.5, [10, 25])).toBeCloseTo(17.5);
    expect(normalizedToRaw(0.5, [22, 30])).toBeCloseTo(26.0);
    expect(normalizedToRaw(0.5, [3.0, 4.8])).toBeCloseTo(3.9);
  });

  it("clamps scores above 1 to range maximum", () => {
    expect(normalizedToRaw(1.5, [10, 25])).toBeCloseTo(25);
  });

  it("clamps negative scores to range minimum", () => {
    expect(normalizedToRaw(-0.2, [10, 25])).toBeCloseTo(10);
  });

  it("handles inverted ranges (max < min) by linear interpolation", () => {
    // For inverted ranges we still return range[0] + score × (range[1] − range[0]);
    // callers should pass [lo, hi] in non-decreasing order.
    expect(normalizedToRaw(0.25, [10, 0])).toBeCloseTo(7.5);
  });
});

describe("AXIS_UNITS (gh-601)", () => {
  it("provides a unit string for every axis", () => {
    expect(AXIS_UNITS.cruise).toBe("m/s");
    expect(AXIS_UNITS.maneuver).toBe("g");
    expect(AXIS_UNITS.wing_loading).toBe("N/m²");
    expect(AXIS_UNITS.glide).toBe("L/D");
    expect(AXIS_UNITS.stall_safety).toBe("×");
  });
});

// gh-601 Part C: computeAxisRanges should union the Ist KPI ranges/values
// so the Ist polygon doesn't collapse to the center when an active mission's
// axis_ranges are narrower than the aircraft's actual KPIs.
const wingRacer: MissionPreset = {
  ...trainer,
  id: "wing_racer",
  axis_ranges: {
    stall_safety: [1.3, 2.5],
    glide: [5, 18],
    climb: [5, 25],
    cruise: [25, 40], // narrower than the actual aircraft (18 m/s)
    maneuver: [2, 5],
    wing_loading: [20, 80],
    field_friendliness: [3, 100],
  },
};

const kpi = (
  axis: AxisName,
  value: number,
  range: [number, number],
  provenance: "computed" | "estimated" | "missing" = "computed",
): MissionAxisKpi => ({
  axis,
  value,
  unit: "-",
  score_0_1: (value - range[0]) / (range[1] - range[0]),
  range_min: range[0],
  range_max: range[1],
  provenance,
  formula: "-",
  warning: null,
});

const istKpiSet = (cruiseValue: number, cruiseRange: [number, number]): MissionKpiSet => ({
  aeroplane_uuid: "x",
  ist_polygon: {
    stall_safety: kpi("stall_safety", 1.6, [1.3, 2.5]),
    glide: kpi("glide", 10, [5, 18]),
    climb: kpi("climb", 12, [5, 25]),
    cruise: kpi("cruise", cruiseValue, cruiseRange),
    maneuver: kpi("maneuver", 3, [2, 5]),
    wing_loading: kpi("wing_loading", 40, [20, 80]),
    field_friendliness: kpi("field_friendliness", 30, [3, 100]),
  },
  target_polygons: [],
  active_mission_id: "wing_racer",
  computed_at: "",
  context_hash: "0".repeat(64),
});

describe("computeAxisRanges with Ist KPIs (gh-601 Part C)", () => {
  it("widens the active mission range to include the Ist KPI's actual value", () => {
    const ist = istKpiSet(18, [10, 25]);
    const ranges = computeAxisRanges([wingRacer], ist);
    // Wing-Racer cruise range is [25, 40]; aircraft cruises at 18 → the
    // returned range must include 18 (and the KPI reference upper bound 25).
    expect(ranges.cruise[0]).toBeLessThanOrEqual(18);
    expect(ranges.cruise[1]).toBeGreaterThanOrEqual(40);
  });

  it("widens the range upward when the Ist value exceeds the preset upper bound", () => {
    const ist = istKpiSet(50, [10, 60]);
    const ranges = computeAxisRanges([wingRacer], ist);
    expect(ranges.cruise[1]).toBeGreaterThanOrEqual(50);
  });

  it("is backward compatible when no Ist KPI is supplied", () => {
    const ranges = computeAxisRanges([wingRacer]);
    expect(ranges.cruise).toEqual([25, 40]);
  });

  it("skips axes whose Ist provenance is missing (no stale-zero pollution)", () => {
    const ist = istKpiSet(0, [0, 1]);
    ist.ist_polygon.cruise = {
      ...ist.ist_polygon.cruise,
      provenance: "missing",
      score_0_1: null,
      value: null,
      range_min: 0,
      range_max: 0,
    };
    const ranges = computeAxisRanges([wingRacer], ist);
    // Cruise range should remain the preset's own [25, 40] since the Ist is
    // missing.
    expect(ranges.cruise).toEqual([25, 40]);
  });

  it("widens ranges across ALL 7 axes when Ist values fall outside", () => {
    const ist: MissionKpiSet = {
      ...istKpiSet(50, [10, 60]),
      ist_polygon: {
        stall_safety: kpi("stall_safety", 3.0, [0.5, 3.0]),
        glide: kpi("glide", 25, [5, 30]),
        climb: kpi("climb", 30, [5, 35]),
        cruise: kpi("cruise", 50, [10, 60]),
        maneuver: kpi("maneuver", 6.0, [1, 6.5]),
        wing_loading: kpi("wing_loading", 100, [10, 120]),
        field_friendliness: kpi("field_friendliness", 120, [3, 150]),
      },
    };
    const ranges = computeAxisRanges([wingRacer], ist);
    expect(ranges.stall_safety[1]).toBeGreaterThanOrEqual(3.0);
    expect(ranges.glide[1]).toBeGreaterThanOrEqual(25);
    expect(ranges.climb[1]).toBeGreaterThanOrEqual(30);
    expect(ranges.cruise[1]).toBeGreaterThanOrEqual(50);
    expect(ranges.maneuver[1]).toBeGreaterThanOrEqual(6.0);
    expect(ranges.wing_loading[1]).toBeGreaterThanOrEqual(100);
    expect(ranges.field_friendliness[1]).toBeGreaterThanOrEqual(120);
  });
});

describe("resolveSollScore (gh-767)", () => {
  const kset = (
    targets: MissionKpiSet["target_polygons"],
  ): MissionKpiSet => ({
    aeroplane_uuid: "x",
    ist_polygon: {} as MissionKpiSet["ist_polygon"],
    target_polygons: targets,
    active_mission_id: "trainer",
    computed_at: "",
    context_hash: "0".repeat(64),
  });

  it("prefers the backend target_polygons score over the preset", async () => {
    const { resolveSollScore } = await import("@/lib/missionScale");
    const kpis = kset([
      {
        mission_id: "trainer",
        label: "Trainer",
        scores_0_1: { cruise: 0.8 },
      },
    ]);
    // preset trainer cruise score is 0.3 — backend 0.8 must win.
    expect(resolveSollScore(kpis, trainer, "cruise")).toBe(0.8);
  });

  it("falls back to the preset score per-axis when the backend omits it", async () => {
    const { resolveSollScore } = await import("@/lib/missionScale");
    // Backend entry exists for trainer but carries only cruise — glide must
    // fall back to the preset (0.4).
    const kpis = kset([
      { mission_id: "trainer", label: "Trainer", scores_0_1: { cruise: 0.8 } },
    ]);
    expect(resolveSollScore(kpis, trainer, "glide")).toBe(0.4);
  });

  it("falls back to the preset polygon when no backend entry matches", async () => {
    const { resolveSollScore } = await import("@/lib/missionScale");
    const kpis = kset([]);
    expect(resolveSollScore(kpis, trainer, "cruise")).toBe(0.3);
  });
});
