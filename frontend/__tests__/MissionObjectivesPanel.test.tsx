import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { MissionObjectivesPanel } from "@/components/workbench/mission/MissionObjectivesPanel";

const updateMock = vi.fn().mockResolvedValue(undefined);

const fullPolygon = {
  stall_safety: 1,
  glide: 0.5,
  climb: 0.5,
  cruise: 0.5,
  maneuver: 0.5,
  wing_loading: 0.5,
  field_friendliness: 0.5,
};

const fullAxisRanges = {
  stall_safety: [1.3, 2.0] as [number, number],
  glide: [15, 35] as [number, number],
  climb: [5, 25] as [number, number],
  cruise: [22, 30] as [number, number], // → 0.5 maps to 26.0
  maneuver: [3.0, 4.8] as [number, number], // → 0.5 maps to 3.9
  wing_loading: [20, 80] as [number, number],
  field_friendliness: [3, 100] as [number, number],
};

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
    update: updateMock,
    isLoading: false, error: null,
  }),
}));

vi.mock("@/hooks/useMissionPresets", () => ({
  useMissionPresets: () => ({
    data: [
      { id: "trainer", label: "Trainer", description: "", target_polygon: fullPolygon, axis_ranges: fullAxisRanges, suggested_estimates: { g_limit: 4, target_static_margin: 0.12, cl_max: 1.4, power_to_weight: 0.4, prop_efficiency: 0.6 } },
      { id: "sailplane", label: "Sailplane", description: "", target_polygon: fullPolygon, axis_ranges: fullAxisRanges, suggested_estimates: { g_limit: 2, target_static_margin: 0.18, cl_max: 1.2, power_to_weight: 0.0, prop_efficiency: 0.0 } },
      { id: "slope_soarer", label: "Slope Soarer", description: "", target_polygon: fullPolygon, axis_ranges: fullAxisRanges, suggested_estimates: { g_limit: 6, target_static_margin: 0.08, cl_max: 1.1, power_to_weight: 0.0, prop_efficiency: 0.0 } },
      { id: "motor_glider", label: "Motor Glider", description: "", target_polygon: fullPolygon, axis_ranges: fullAxisRanges, suggested_estimates: { g_limit: 5.3, target_static_margin: 0.10, cl_max: 1.4, power_to_weight: 100, prop_efficiency: 0.65 } },
      { id: "flying_wing", label: "Flying Wing", description: "", target_polygon: fullPolygon, axis_ranges: fullAxisRanges, suggested_estimates: { g_limit: 5.0, target_static_margin: 0.075, cl_max: 1.0, power_to_weight: 100, prop_efficiency: 0.65 } },
    ],
    isLoading: false, error: null,
  }),
}));

describe("MissionObjectivesPanel", () => {
  beforeEach(() => {
    updateMock.mockClear();
  });

  it("renders the mission type dropdown with all presets", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    expect(screen.getByRole("option", { name: /Trainer/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Sailplane/ })).toBeInTheDocument();
    // gh-582: slope_soarer surfaces in the selector once the backend seeds it.
    expect(screen.getByRole("option", { name: /Slope Soarer/ })).toBeInTheDocument();
    // gh-580: motor_glider surfaces in the selector once seeded.
    expect(screen.getByRole("option", { name: /Motor Glider/ })).toBeInTheDocument();
    // gh-581: flying_wing surfaces in the selector once seeded.
    expect(screen.getByRole("option", { name: /Flying Wing/ })).toBeInTheDocument();
  });

  it("renders the field-performance section", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    expect(screen.getByText(/Field Performance/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Available Runway/i)).toBeInTheDocument();
  });

  it("shows the apply banner after mission_type change with English copy (gh-601)", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    const select = screen.getByLabelText(/Mission Type/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "motor_glider" } });

    const banner = screen.getByTestId("mission-apply-banner");
    expect(banner).toBeInTheDocument();

    // English banner copy — no remaining German.
    expect(banner.textContent ?? "").toMatch(/Mission set to/i);
    expect(banner.textContent ?? "").not.toMatch(/Mission auf/i);
    expect(banner.textContent ?? "").not.toMatch(/angepasst/i);
  });

  it("shows a diff row for target_cruise_mps after Motor Glider preset change (gh-601)", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    const select = screen.getByLabelText(/Mission Type/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "motor_glider" } });

    // cruise: 18 → 26.0 (0.5 × (22, 30))
    expect(screen.getByTestId("diff-row-target_cruise_mps")).toBeInTheDocument();
  });

  it("applies all 6 target fields when Apply is clicked (gh-601)", async () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    const select = screen.getByLabelText(/Mission Type/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "motor_glider" } });

    const applyBtn = screen.getByRole("button", { name: /^Apply$/ });
    fireEvent.click(applyBtn);

    // Banner is dismissed
    expect(screen.queryByTestId("mission-apply-banner")).not.toBeInTheDocument();

    // update() was called with all 6 target fields set to preset-derived values
    await waitFor(() => {
      expect(updateMock).toHaveBeenCalled();
    });
    const lastCallArg = updateMock.mock.calls[updateMock.mock.calls.length - 1][0];
    expect(lastCallArg.target_cruise_mps).toBeCloseTo(26.0, 3);
    expect(lastCallArg.target_maneuver_n).toBeCloseTo(3.9, 3);
    // stall_safety: preset score is 1.0 → range[1] = 2.0
    expect(lastCallArg.target_stall_safety).toBeCloseTo(2.0, 3);
    // glide: 0.5 × (15, 35) = 25
    expect(lastCallArg.target_glide_ld).toBeCloseTo(25.0, 3);
    // climb: 0.5 × (5, 25) = 15
    expect(lastCallArg.target_climb_energy).toBeCloseTo(15.0, 3);
    // wing_loading: 0.5 × (20, 80) = 50
    expect(lastCallArg.target_wing_loading_n_m2).toBeCloseTo(50.0, 3);
    // mission_type carries through
    expect(lastCallArg.mission_type).toBe("motor_glider");
  });

  it("does not apply targets when Dismiss is clicked (gh-601)", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    const select = screen.getByLabelText(/Mission Type/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "motor_glider" } });

    const dismissBtn = screen.getByRole("button", { name: /Dismiss/ });
    fireEvent.click(dismissBtn);

    expect(screen.queryByTestId("mission-apply-banner")).not.toBeInTheDocument();

    // The only update() call so far is from the debounced mission_type set
    // (debounce timer hasn't fired in synchronous test). It must NOT contain
    // the preset target overrides.
    for (const call of updateMock.mock.calls) {
      const arg = call[0];
      // Targets remain at the original (trainer) values.
      expect(arg.target_cruise_mps).toBe(18);
      expect(arg.target_glide_ld).toBe(12);
    }
  });
});
