import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MissionObjectivesPanel } from "@/components/workbench/mission/MissionObjectivesPanel";

vi.mock("@/hooks/useMissionObjectives", () => ({
  useMissionObjectives: () => ({
    data: {
      mission_type: "trainer",
      target_cruise_mps: 18, target_stall_safety: 1.8,
      target_maneuver_n: 3, target_glide_ld: 12,
      target_climb_energy: 22, target_wing_loading_n_m2: 412,
      target_field_length_m: 50,
      available_runway_m: 50, runway_type: "grass",
      t_static_N: 18, takeoff_mode: "runway",
    },
    update: vi.fn().mockResolvedValue(undefined),
    isLoading: false, error: null,
  }),
}));

vi.mock("@/hooks/useMissionPresets", () => ({
  useMissionPresets: () => ({
    data: [
      { id: "trainer", label: "Trainer", description: "", target_polygon: {}, axis_ranges: {}, suggested_estimates: { g_limit: 4, target_static_margin: 0.12, cl_max: 1.4, power_to_weight: 0.4, prop_efficiency: 0.6 } },
      { id: "sailplane", label: "Sailplane", description: "", target_polygon: {}, axis_ranges: {}, suggested_estimates: { g_limit: 2, target_static_margin: 0.18, cl_max: 1.2, power_to_weight: 0.0, prop_efficiency: 0.0 } },
    ],
    isLoading: false, error: null,
  }),
}));

describe("MissionObjectivesPanel", () => {
  it("renders the mission type dropdown with all presets", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    expect(screen.getByRole("option", { name: /Trainer/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Sailplane/ })).toBeInTheDocument();
  });

  it("renders the field-performance section", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    expect(screen.getByText(/Field Performance/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Available Runway/i)).toBeInTheDocument();
  });

  it("shows the auto-apply banner after mission_type change", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    const select = screen.getByLabelText(/Mission Type/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "sailplane" } });
    expect(screen.getByText(/Estimates angepasst/i)).toBeInTheDocument();
  });
});
