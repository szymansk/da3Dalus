import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MissionCompliancePanel } from "@/components/workbench/mission/MissionCompliancePanel";

vi.mock("@/hooks/useMissionObjectives", () => ({
  useMissionObjectives: () => ({
    data: { mission_type: "trainer" },
  }),
}));

vi.mock("@/hooks/useMissionPresets", () => ({
  useMissionPresets: () => ({
    data: [
      {
        id: "trainer",
        label: "Trainer",
        description: "",
        target_polygon: {
          stall_safety: 0.5,
          glide: 0.5,
          climb: 0.5,
          cruise: 0.5,
          maneuver: 0.5,
          wing_loading: 0.5,
          field_friendliness: 0.5,
        },
        axis_ranges: {
          stall_safety: [0, 1],
          glide: [0, 1],
          climb: [0, 1],
          cruise: [0, 1],
          maneuver: [0, 1],
          wing_loading: [0, 1],
          field_friendliness: [0, 1],
        },
        suggested_estimates: {
          g_limit: 4,
          target_static_margin: 0.12,
          cl_max: 1.4,
          power_to_weight: 0.4,
          prop_efficiency: 0.6,
        },
      },
      {
        id: "sailplane",
        label: "Sailplane",
        description: "",
        target_polygon: {
          stall_safety: 0.5,
          glide: 0.5,
          climb: 0.5,
          cruise: 0.5,
          maneuver: 0.5,
          wing_loading: 0.5,
          field_friendliness: 0.5,
        },
        axis_ranges: {
          stall_safety: [0, 1],
          glide: [0, 1],
          climb: [0, 1],
          cruise: [0, 1],
          maneuver: [0, 1],
          wing_loading: [0, 1],
          field_friendliness: [0, 1],
        },
        suggested_estimates: {
          g_limit: 2,
          target_static_margin: 0.18,
          cl_max: 1.2,
          power_to_weight: 0.0,
          prop_efficiency: 0.0,
        },
      },
    ],
  }),
}));

const FAKE_KPI = (axis: string) => ({
  axis,
  value: 0.5,
  unit: null,
  score_0_1: 0.5,
  range_min: 0,
  range_max: 1,
  provenance: "computed" as const,
  formula: "",
  warning: null,
});

vi.mock("@/hooks/useMissionKpis", () => ({
  useMissionKpis: () => ({
    data: {
      aeroplane_uuid: "x",
      ist_polygon: {
        stall_safety: FAKE_KPI("stall_safety"),
        glide: FAKE_KPI("glide"),
        climb: FAKE_KPI("climb"),
        cruise: FAKE_KPI("cruise"),
        maneuver: FAKE_KPI("maneuver"),
        wing_loading: FAKE_KPI("wing_loading"),
        field_friendliness: FAKE_KPI("field_friendliness"),
      },
      target_polygons: [],
      active_mission_id: "trainer",
      computed_at: "now",
      context_hash: "x",
    },
  }),
}));

describe("MissionCompliancePanel", () => {
  it("renders the title and radar chart", () => {
    render(
      <MissionCompliancePanel aeroplaneId="x" onAxisClick={() => {}} />,
    );
    expect(screen.getByText(/Mission Compliance/)).toBeInTheDocument();
    expect(screen.getByText(/Vergleichs-Profile/)).toBeInTheDocument();
  });

  it("adds a comparison mission when a non-active toggle is clicked", () => {
    render(
      <MissionCompliancePanel aeroplaneId="x" onAxisClick={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Sailplane/ }));
    // Sky-blue (comparison) class should appear on Sailplane after toggle.
    const sailplane = screen.getByRole("button", { name: /Sailplane/ });
    expect(sailplane.className).toContain("text-sky-400");
  });
});
