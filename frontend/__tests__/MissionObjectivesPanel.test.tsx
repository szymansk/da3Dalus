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

// Default mission-objective payload — individual tests can override
// the per-aeroplane payload via `setMissionData(id, data)` (gh-602).
const defaultMissionData = {
  mission_type: "trainer",
  target_cruise_mps: 18, target_stall_safety: 1.8,
  target_maneuver_n: 3, target_glide_ld: 12,
  target_climb_energy: 22, target_wing_loading_n_m2: 412,
  target_field_length_m: 50,
  available_runway_m: 50, runway_type: "grass",
  t_static_N: 18, takeoff_mode: "runway",
};

// Per-aeroplaneId mission-data store used by the mock.
const missionDataById = new Map<string, typeof defaultMissionData>();
const setMissionData = (id: string, data: typeof defaultMissionData) => {
  missionDataById.set(id, data);
};
const resetMissionData = () => {
  missionDataById.clear();
};

vi.mock("@/hooks/useMissionObjectives", () => ({
  useMissionObjectives: (aeroplaneId: string | null) => ({
    data: missionDataById.get(aeroplaneId ?? "") ?? defaultMissionData,
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
    resetMissionData();
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

  it("reloads draft from new persisted data when aeroplaneId changes (gh-602)", () => {
    setMissionData("a", { ...defaultMissionData, target_cruise_mps: 18 });
    setMissionData("b", { ...defaultMissionData, target_cruise_mps: 42 });

    const { rerender } = render(<MissionObjectivesPanel aeroplaneId="a"/>);
    // Aeroplane A's cruise value (18) is shown.
    const inputA = screen.getByLabelText(/Target Cruise/i) as HTMLInputElement;
    expect(inputA.value).toBe("18");

    // User switches to aeroplane B — its persisted data differs.
    rerender(<MissionObjectivesPanel aeroplaneId="b"/>);
    const inputB = screen.getByLabelText(/Target Cruise/i) as HTMLInputElement;
    expect(inputB.value).toBe("42");
    expect(inputB.value).not.toBe("18");
  });

  describe("per-field info tooltips (gh-610)", () => {
    // The 11 expected tooltip texts. Keep in lockstep with FIELD_DESCRIPTIONS
    // in MissionObjectivesPanel — if the prod copy changes, this test should
    // fail and surface the divergence.
    const TOOLTIPS: Record<string, string> = {
      "Mission Type":
        "Preset that suggests defaults for the editable performance targets and the design assumptions. Changing the preset applies its suggested values via the banner Apply button.",
      "Target Cruise":
        "Design cruise speed at altitude. Drives propeller selection, drag analysis, and the cruise-constraint curve on the matching chart.",
      "Stall Safety":
        "Safety factor on stall speed (×); e.g. 1.8 means landing approach at 1.8 × V_stall. Lower = closer to stall = more demanding pilot skill.",
      "Max Maneuver":
        "Limit load factor n_max (g). Sets structural g-loading; CS-22 utility category = 5.3, aerobatic = 6+.",
      "Min Glide (L/D)":
        "Minimum lift-to-drag ratio in the cruise polar. Sailplanes ≥ 20; sport ≥ 10; trainer ≥ 8.",
      "Climb Energy":
        "Energy-per-time proxy for climb performance: rate-of-climb × g-load. Higher = stronger powerplant relative to weight.",
      "Target Wing Load":
        "Design wing loading W/S (N/m²). Sets stall speed and the W/S-axis position on the matching chart. Higher = smaller wing but higher stall speed.",
      "Available Runway":
        "Hard ground length available for take-off / landing (m). Sets the take-off and landing constraint curves on the matching chart.",
      "Runway Type":
        "Surface affecting rolling friction (grass higher, asphalt lower) and crash-landing tolerance (belly = no gear).",
      "Static Thrust":
        "Powertrain static thrust at zero airspeed (N). Sets the T/W ratio on the matching chart. For gliders, 0.",
      "Takeoff Mode":
        "runway = wheeled take-off; hand_launch = thrown by hand (RC); bungee = elastic catapult (gliders); catapult = launched device.",
    };

    it("renders 11 tooltip elements — one per editable input + Mission Type", () => {
      render(<MissionObjectivesPanel aeroplaneId="x" />);
      // role="tooltip" elements are hidden via Tailwind `hidden` class but
      // still in the DOM so screen readers and `screen.getAllByRole` find them.
      const tips = screen.getAllByRole("tooltip", { hidden: true });
      expect(tips.length).toBe(11);
    });

    it("each tooltip text matches the spec exactly", () => {
      render(<MissionObjectivesPanel aeroplaneId="x" />);
      const tipTexts = screen
        .getAllByRole("tooltip", { hidden: true })
        .map((el) => el.textContent ?? "");
      for (const expected of Object.values(TOOLTIPS)) {
        expect(tipTexts).toContain(expected);
      }
    });

    it("Mission Type dropdown has its info tooltip", () => {
      render(<MissionObjectivesPanel aeroplaneId="x" />);
      const tips = screen.getAllByRole("tooltip", { hidden: true });
      const has = tips.some((t) => t.textContent === TOOLTIPS["Mission Type"]);
      expect(has).toBe(true);
    });
  });

  // Coverage for each per-field onChange closure (gh-610). Firing a value
  // change exercises the inline `(v) => set("...", v)` handler on every
  // NumField/SelectField, ensuring the description-prop refactor did not
  // silently break wiring.
  describe("per-field onChange handlers (gh-610 coverage)", () => {
    it.each([
      ["Target Cruise", "21"],
      ["Stall Safety", "1.6"],
      ["Max Maneuver", "4"],
      ["Min Glide (L/D)", "14"],
      ["Climb Energy", "20"],
      ["Target Wing Load", "300"],
      ["Available Runway", "75"],
      ["Static Thrust", "12"],
    ])("NumField %s onChange wires through to draft", (label, newValue) => {
      render(<MissionObjectivesPanel aeroplaneId="x"/>);
      // Use exact-string match so labels with regex metachars like "Min Glide (L/D)"
      // do not get parsed as regex groups.
      const input = screen.getByLabelText(label, { exact: true }) as HTMLInputElement;
      fireEvent.change(input, { target: { value: newValue } });
      expect(input.value).toBe(newValue);
    });

    it.each([
      ["Runway Type", "asphalt"],
      ["Takeoff Mode", "hand_launch"],
    ])("SelectField %s onChange wires through to draft", (label, newValue) => {
      render(<MissionObjectivesPanel aeroplaneId="x"/>);
      const select = screen.getByLabelText(label, { exact: true }) as HTMLSelectElement;
      fireEvent.change(select, { target: { value: newValue } });
      expect(select.value).toBe(newValue);
    });

    it("debounced update() fires 300 ms after a value change", () => {
      vi.useFakeTimers();
      try {
        render(<MissionObjectivesPanel aeroplaneId="x"/>);
        const input = screen.getByLabelText(/Target Cruise/i) as HTMLInputElement;
        fireEvent.change(input, { target: { value: "33" } });
        // Before the debounce fires, update() has not been called.
        expect(updateMock).not.toHaveBeenCalled();
        vi.advanceTimersByTime(350);
        expect(updateMock).toHaveBeenCalled();
        const arg = updateMock.mock.calls[updateMock.mock.calls.length - 1][0];
        expect(arg.target_cruise_mps).toBe(33);
      } finally {
        vi.useRealTimers();
      }
    });
  });

  it("preserves in-flight draft edits across SWR revalidations for the SAME aeroplaneId (gh-602)", () => {
    setMissionData("a", { ...defaultMissionData, target_cruise_mps: 10 });

    const { rerender } = render(<MissionObjectivesPanel aeroplaneId="a"/>);
    const input = screen.getByLabelText(/Target Cruise/i) as HTMLInputElement;
    expect(input.value).toBe("10");

    // User edits the cruise value to 99.
    fireEvent.change(input, { target: { value: "99" } });
    expect(input.value).toBe("99");

    // SWR revalidates the SAME aeroplane — server still returns 10
    // (the user's 99 hasn't been persisted yet). The draft must NOT be
    // clobbered by this revalidation.
    setMissionData("a", { ...defaultMissionData, target_cruise_mps: 10 });
    rerender(<MissionObjectivesPanel aeroplaneId="a"/>);

    const inputAfter = screen.getByLabelText(/Target Cruise/i) as HTMLInputElement;
    expect(inputAfter.value).toBe("99");
  });
});
