import { describe, it, expect } from "vitest";
import { computeAxisRanges } from "@/lib/missionScale";
import type { MissionPreset } from "@/hooks/useMissionPresets";

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
