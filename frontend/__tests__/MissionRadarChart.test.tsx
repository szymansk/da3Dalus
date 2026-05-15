import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { MissionRadarChart } from "@/components/workbench/mission/MissionRadarChart";
import type { MissionKpiSet, MissionAxisKpi } from "@/hooks/useMissionKpis";
import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";

const baseKpi = (axis: AxisName, score: number): MissionAxisKpi => ({
  axis,
  value: 1,
  unit: "-",
  score_0_1: score,
  range_min: 0,
  range_max: 1,
  provenance: "computed",
  formula: "-",
  warning: null,
});

const kset: MissionKpiSet = {
  aeroplane_uuid: "x",
  ist_polygon: {
    stall_safety: baseKpi("stall_safety", 0.5),
    glide: baseKpi("glide", 0.5),
    climb: baseKpi("climb", 0.5),
    cruise: baseKpi("cruise", 0.5),
    maneuver: baseKpi("maneuver", 0.5),
    wing_loading: baseKpi("wing_loading", 0.5),
    field_friendliness: baseKpi("field_friendliness", 0.5),
  },
  target_polygons: [],
  active_mission_id: "trainer",
  computed_at: "",
  context_hash: "0".repeat(64),
};

const preset = (id: string): MissionPreset => ({
  id,
  label: id,
  description: "",
  target_polygon: {
    stall_safety: 1,
    glide: 0.5,
    climb: 0.5,
    cruise: 0.5,
    maneuver: 0.5,
    wing_loading: 0.5,
    field_friendliness: 0.5,
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
});

describe("MissionRadarChart", () => {
  it("renders the base Ist polygon plus grid rings", () => {
    const { container } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    const polys = container.querySelectorAll("polygon");
    // grid outer (1) + grid rings (3) + active soll (1) + ist (1) >= 5
    expect(polys.length).toBeGreaterThanOrEqual(5);
  });

  it("renders ghost polygons for additional active missions", () => {
    const { container } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer"), preset("sailplane")]}
        onAxisClick={() => undefined}
      />,
    );
    const ghosts = container.querySelectorAll(".radar-ghost");
    expect(ghosts.length).toBe(1);
  });

  it("invokes onAxisClick with axis name when an axis label is clicked", () => {
    const onAxisClick = vi.fn();
    const { container } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer")]}
        onAxisClick={onAxisClick}
      />,
    );
    const labels = container.querySelectorAll("[data-axis]");
    expect(labels.length).toBe(7);
    (labels[0] as HTMLElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true }),
    );
    expect(onAxisClick).toHaveBeenCalledTimes(1);
  });
});
