import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import React from "react";
import {
  MissionRadarChart,
  tooltipAnchor,
} from "@/components/workbench/mission/MissionRadarChart";
import { AXES } from "@/lib/missionScale";
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

describe("tooltipAnchor (gh-609)", () => {
  // 7-axis radar: i=0 stall_safety, 1 glide, 2 climb, 3 cruise,
  //               4 maneuver,    5 wing_loading, 6 field_friendliness
  it("anchors top-half axes with yAlign='top' (sin < 0)", () => {
    // i=0 → angle=-π/2 → sin=-1 → top half
    const a = tooltipAnchor(0, 7);
    expect(a.yAlign).toBe("top");
    // dy should be positive (push down away from label)
    expect(a.dy).toBeGreaterThan(0);
  });

  it("anchors bottom-half axes with yAlign='bottom' (sin > 0)", () => {
    // i=3 (cruise) → sin≈+0.90 → bottom half
    const a = tooltipAnchor(3, 7);
    expect(a.yAlign).toBe("bottom");
    expect(a.dy).toBeLessThan(0);
  });

  it("anchors right-half axes with xAlign='right' (cos > 0)", () => {
    // i=2 (climb) → cos≈+0.97 → right half
    const a = tooltipAnchor(2, 7);
    expect(a.xAlign).toBe("right");
    expect(a.dx).toBeLessThan(0);
  });

  it("anchors left-half axes with xAlign='left' (cos < 0)", () => {
    // i=5 (wing_loading) → cos≈-0.97 → left half
    const a = tooltipAnchor(5, 7);
    expect(a.xAlign).toBe("left");
    expect(a.dx).toBeGreaterThan(0);
  });

  it("uses zero horizontal offset for near-vertical axes (|cos| < 0.2)", () => {
    // i=0 (stall_safety) → cos=0 → no horizontal nudge
    const a = tooltipAnchor(0, 7);
    expect(a.dx).toBe(0);
  });

  it("uses zero vertical offset for near-horizontal axes (|sin| < 0.2)", () => {
    // For n=4, i=1 → angle=0 → cos=1, sin=0 → no vertical nudge
    const a = tooltipAnchor(1, 4);
    expect(a.dy).toBe(0);
  });
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

  it("renders active mission label in the tooltip header, not on the Soll row (gh-617)", () => {
    const ksetCruise = {
      ...kset,
      ist_polygon: { ...kset.ist_polygon, cruise: cruiseKpi },
    };
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={ksetCruise}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));

    // Header has axis name AND the active mission label, separated by " · ".
    const header = getByTestId("axis-tooltip-cruise-header");
    const headerText = header.textContent ?? "";
    expect(headerText).toMatch(/Cruise/);
    expect(headerText).toMatch(/trainer/);
    // Both pieces are present with a "·" separator (regardless of order).
    expect(headerText).toMatch(/·/);

    // Soll row contains only value + unit (no trailing parenthesised label).
    // Spans are inline; textContent concatenates without spaces between them,
    // hence "Soll:17.50 m/s". The `$` anchor verifies no trailing "(...)".
    const sollRow = getByTestId("axis-tooltip-cruise-soll");
    const sollText = (sollRow.textContent ?? "").trim();
    expect(sollText).toMatch(/^Soll:\s*\d+\.\d+\s+m\/s$/);
    // No trailing "(trainer)" suffix on the Soll row.
    expect(sollText).not.toMatch(/\(trainer\)/);
  });

  it("header degrades to just the axis name when no active mission is selected (gh-617)", () => {
    const ksetCruise = {
      ...kset,
      ist_polygon: { ...kset.ist_polygon, cruise: cruiseKpi },
    };
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={ksetCruise}
        activeMissions={[]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));
    const header = getByTestId("axis-tooltip-cruise-header");
    const headerText = (header.textContent ?? "").trim();
    expect(headerText).toBe("Cruise");
    // No separator when no active mission is present.
    expect(headerText).not.toMatch(/·/);
  });

  it("ghost rows still carry their own per-row profile label (gh-617)", () => {
    const ghost = preset("sailplane");
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

    // Header carries the ACTIVE mission only ("trainer"), not the ghost.
    const header = getByTestId("axis-tooltip-cruise-header");
    expect(header.textContent ?? "").toMatch(/trainer/);
    expect(header.textContent ?? "").not.toMatch(/sailplane/);

    // Ghost row preserves the "<label>: <value> <unit>" format.
    const tooltip = getByTestId("axis-tooltip-cruise");
    const text = tooltip.textContent ?? "";
    // Format: "sailplane: 26.00 m/s"
    expect(text).toMatch(/sailplane:\s*26\.00\s+m\/s/);
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

  it("anchors tooltip to the right (extends leftward) on right-half axes (gh-609)", () => {
    // Cruise sits at i=3 → cos≈0.43 > 0 → right half → xAlign='right'.
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));
    const tooltip = getByTestId("axis-tooltip-cruise");
    expect(tooltip.getAttribute("data-x-align")).toBe("right");
    // The inner div should be text-aligned to the right.
    const innerDiv = tooltip.firstElementChild as HTMLElement;
    expect(innerDiv?.style.textAlign).toBe("right");
  });

  it("anchors tooltip to the left (extends rightward) on left-half axes (gh-609)", () => {
    // Wing-loading sits at i=5 → cos≈-0.97 < 0 → left half → xAlign='left'.
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-wing_loading"));
    const tooltip = getByTestId("axis-tooltip-wing_loading");
    expect(tooltip.getAttribute("data-x-align")).toBe("left");
    const innerDiv = tooltip.firstElementChild as HTMLElement;
    expect(innerDiv?.style.textAlign).toBe("left");
  });

  it("keeps every axis tooltip inside the SVG viewBox (gh-609)", () => {
    // viewBox is "-150 -150 300 300" → bounds [-150, 150] in both axes.
    const VIEW_MIN = -150;
    const VIEW_MAX = 150;
    const BOX_W = 150;
    const BASE_H = 56; // matches MissionRadarChart's baseH for no ghosts
    for (const axis of AXES) {
      const { getByTestId, unmount } = render(
        <MissionRadarChart
          kpis={kset}
          activeMissions={[preset("trainer")]}
          onAxisClick={() => undefined}
        />,
      );
      fireEvent.mouseEnter(getByTestId(`hover-wedge-${axis}`));
      const tooltip = getByTestId(`axis-tooltip-${axis}`);
      const x = Number(tooltip.getAttribute("x"));
      const y = Number(tooltip.getAttribute("y"));
      const w = Number(tooltip.getAttribute("width") ?? BOX_W);
      const h = Number(tooltip.getAttribute("height") ?? BASE_H);
      // Allow a small slack (8px) for the visual anchor nudge — but never
      // more than the viewBox.
      expect(x).toBeGreaterThanOrEqual(VIEW_MIN - 8);
      expect(x + w).toBeLessThanOrEqual(VIEW_MAX + 8);
      expect(y).toBeGreaterThanOrEqual(VIEW_MIN - 8);
      expect(y + h).toBeLessThanOrEqual(VIEW_MAX + 8);
      unmount();
    }
  });

  it("derives the Soll line from kpis.target_polygons, not the static preset (gh-767)", () => {
    // Backend supplies an objective-derived Soll: cruise score 0.8.
    // trainer preset cruise range [10,25] → 10 + 0.8×15 = 22.00.
    // The static preset's cruise target_polygon is 0.5 → 17.50 (the stale value).
    const ksetWithTargets: MissionKpiSet = {
      ...kset,
      ist_polygon: { ...kset.ist_polygon, cruise: cruiseKpi },
      target_polygons: [
        {
          mission_id: "trainer",
          label: "trainer",
          scores_0_1: {
            stall_safety: 0.5,
            glide: 0.5,
            climb: 0.5,
            cruise: 0.8,
            maneuver: 0.5,
            wing_loading: 0.5,
            field_friendliness: 1.0,
          },
        },
      ],
    };
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={ksetWithTargets}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));
    const sollRow = getByTestId("axis-tooltip-cruise-soll");
    const text = sollRow.textContent ?? "";
    // Reflects the backend (user-target) score 0.8 → 22.00 …
    expect(text).toMatch(/22\.00/);
    // … and NOT the static preset value 0.5 → 17.50.
    expect(text).not.toMatch(/17\.50/);
  });

  it("falls back to the preset polygon when the backend supplies no target score (gh-767)", () => {
    // Empty target_polygons → keep using the static preset (legacy behaviour).
    const ksetCruise = {
      ...kset,
      ist_polygon: { ...kset.ist_polygon, cruise: cruiseKpi },
    };
    const { getByTestId } = render(
      <MissionRadarChart
        kpis={ksetCruise}
        activeMissions={[preset("trainer")]}
        onAxisClick={() => undefined}
      />,
    );
    fireEvent.mouseEnter(getByTestId("hover-wedge-cruise"));
    const sollRow = getByTestId("axis-tooltip-cruise-soll");
    // preset cruise 0.5 → 10 + 0.5×15 = 17.50.
    expect(sollRow.textContent ?? "").toMatch(/17\.50/);
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
