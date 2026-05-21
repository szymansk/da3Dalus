import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
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

const cruiseKpi: MissionAxisKpi = {
  axis: "cruise",
  value: 18.2,
  unit: "m/s",
  score_0_1: 0.5,
  range_min: 10,
  range_max: 25,
  provenance: "computed",
  formula: "-",
  warning: null,
};

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

  it("renders a hover wedge per axis (gh-601)", () => {
    const { container } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    const wedges = container.querySelectorAll('[data-testid^="hover-wedge-"]');
    expect(wedges.length).toBe(7);
  });

  it("shows tooltip with raw cruise value on axis hover (gh-601)", () => {
    const ksetCruise = { ...kset, ist_polygon: { ...kset.ist_polygon, cruise: cruiseKpi } };
    const { getByTestId, queryByTestId } = render(
      <MissionRadarChart
        kpis={ksetCruise}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    expect(queryByTestId("axis-tooltip-cruise")).not.toBeInTheDocument();

    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));

    const tooltip = getByTestId("axis-tooltip-cruise");
    expect(tooltip).toBeInTheDocument();
    const text = tooltip.textContent ?? "";
    // Ist: 10 + 0.5 × (25 − 10) = 17.50
    expect(text).toMatch(/17\.50/);
    expect(text).toMatch(/m\/s/);
    // Soll for trainer preset: 10 + 0.5 × (25 − 10) = 17.50
    expect(text).toMatch(/Soll/);
  });

  it("hides tooltip on mouseleave (gh-601)", () => {
    const { getByTestId, queryByTestId } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    const wedge = getByTestId("hover-wedge-cruise");
    fireEvent.mouseEnter(wedge);
    expect(queryByTestId("axis-tooltip-cruise")).toBeInTheDocument();
    fireEvent.mouseLeave(wedge);
    expect(queryByTestId("axis-tooltip-cruise")).not.toBeInTheDocument();
  });

  it("does not collapse Ist polygon when preset's axis_ranges are narrower than the actual KPI (gh-601 Part C)", () => {
    // Wing-Racer style preset with cruise range [25, 40].
    const wingRacer = preset("wing_racer");
    wingRacer.axis_ranges = {
      stall_safety: [1.3, 2.5],
      glide: [5, 18],
      climb: [5, 25],
      cruise: [25, 40],
      maneuver: [2, 5],
      wing_loading: [20, 80],
      field_friendliness: [3, 100],
    };
    // Aircraft cruises at 18 m/s — below the Wing-Racer preset's lower bound.
    const ksetLowCruise: MissionKpiSet = {
      ...kset,
      ist_polygon: {
        ...kset.ist_polygon,
        cruise: {
          axis: "cruise",
          value: 18,
          unit: "m/s",
          score_0_1: 0.4,
          range_min: 10,
          range_max: 30,
          provenance: "computed",
          formula: "-",
          warning: null,
        },
      },
    };
    const { container } = render(
      <MissionRadarChart
        kpis={ksetLowCruise}
        activeMissions={[wingRacer]}
        onAxisClick={() => undefined}
      />,
    );
    const ist = container.querySelector("polygon.radar-ist");
    expect(ist).not.toBeNull();
    const pointsAttr = ist!.getAttribute("points") ?? "";
    // Parse points and ensure at least one vertex is > 5 px from origin.
    const distances = pointsAttr
      .trim()
      .split(/\s+/)
      .map((p) => p.split(",").map(Number))
      .map(([x, y]) => Math.hypot(x, y));
    expect(Math.max(...distances)).toBeGreaterThan(5);
  });

  it("includes ghost mission values in tooltip (gh-601)", () => {
    const ghost = preset("sailplane");
    // Set a distinctive cruise score on the ghost so we can locate it.
    ghost.target_polygon.cruise = 0.8;
    ghost.axis_ranges.cruise = [10, 30]; // 10 + 0.8 × 20 = 26
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer"), ghost]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));
    const tooltip = getByTestId("axis-tooltip-cruise");
    const text = tooltip.textContent ?? "";
    // Ghost label "sailplane" is present
    expect(text).toMatch(/sailplane/);
    // Ghost value 26.00
    expect(text).toMatch(/26\.00/);
  });
});
