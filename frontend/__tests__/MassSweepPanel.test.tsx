import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { MassSweepData } from "@/hooks/useMassSweep";

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

import { MassSweepPanel } from "@/components/workbench/MassSweepPanel";

const FAKE_SWEEP: MassSweepData = {
  s_ref: 0.42,
  cl_max: 1.5,
  velocity: 15.0,
  altitude: 0.0,
  points: [
    { mass_kg: 1.0, wing_loading_pa: 23.4, stall_speed_ms: 8.1, required_cl: 0.3, cl_margin: 1.2 },
    { mass_kg: 2.0, wing_loading_pa: 46.8, stall_speed_ms: 11.5, required_cl: 0.6, cl_margin: 0.9 },
    { mass_kg: 3.0, wing_loading_pa: 70.1, stall_speed_ms: 14.1, required_cl: 0.9, cl_margin: 0.6 },
    { mass_kg: 5.0, wing_loading_pa: 116.9, stall_speed_ms: 18.2, required_cl: 1.5, cl_margin: 0.0 },
    { mass_kg: 6.0, wing_loading_pa: 140.3, stall_speed_ms: 19.9, required_cl: 1.8, cl_margin: -0.3 },
  ],
};

describe("MassSweepPanel", () => {
  it("shows empty state when data is null and not computing", () => {
    render(
      <MassSweepPanel
        data={null}
        isComputing={false}
        error={null}
        onCompute={vi.fn()}
        currentMassKg={null}
      />,
    );
    expect(
      screen.getByText(/click.*compute.*to visualize/i),
    ).toBeInTheDocument();
  });

  it("shows computing state", () => {
    render(
      <MassSweepPanel
        data={null}
        isComputing={true}
        error={null}
        onCompute={vi.fn()}
        currentMassKg={null}
      />,
    );
    expect(screen.getByText("Computing mass sweep...")).toBeInTheDocument();
  });

  it("shows error banner", () => {
    render(
      <MassSweepPanel
        data={null}
        isComputing={false}
        error="Something went wrong"
        onCompute={vi.fn()}
        currentMassKg={null}
      />,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("calls onCompute when Compute button is clicked", async () => {
    const onCompute = vi.fn();
    const user = userEvent.setup();
    render(
      <MassSweepPanel
        data={null}
        isComputing={false}
        error={null}
        onCompute={onCompute}
        currentMassKg={null}
      />,
    );
    await user.click(screen.getByRole("button", { name: /compute mass sweep/i }));
    expect(onCompute).toHaveBeenCalledOnce();
    const args = onCompute.mock.calls[0][0];
    expect(args).toHaveProperty("velocity");
    expect(args).toHaveProperty("altitude");
  });

  it("disables compute button when isComputing", () => {
    render(
      <MassSweepPanel
        data={FAKE_SWEEP}
        isComputing={true}
        error={null}
        onCompute={vi.fn()}
        currentMassKg={2.5}
      />,
    );
    expect(screen.getByRole("button", { name: /computing/i })).toBeDisabled();
  });

  it("renders chart container when data is present", () => {
    render(
      <MassSweepPanel
        data={FAKE_SWEEP}
        isComputing={false}
        error={null}
        onCompute={vi.fn()}
        currentMassKg={2.5}
      />,
    );
    expect(screen.getByTestId("mass-sweep-chart")).toBeInTheDocument();
  });

  it("renders velocity and altitude inputs", () => {
    render(
      <MassSweepPanel
        data={null}
        isComputing={false}
        error={null}
        onCompute={vi.fn()}
        currentMassKg={null}
      />,
    );
    expect(screen.getByLabelText(/velocity/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/altitude/i)).toBeInTheDocument();
  });

  it("passes velocity and altitude values to onCompute", async () => {
    const onCompute = vi.fn();
    const user = userEvent.setup();
    render(
      <MassSweepPanel
        data={null}
        isComputing={false}
        error={null}
        onCompute={onCompute}
        currentMassKg={null}
      />,
    );

    const velocityInput = screen.getByLabelText(/velocity/i);
    await user.clear(velocityInput);
    await user.type(velocityInput, "20");

    const altitudeInput = screen.getByLabelText(/altitude/i);
    await user.clear(altitudeInput);
    await user.type(altitudeInput, "500");

    await user.click(screen.getByRole("button", { name: /compute mass sweep/i }));
    expect(onCompute).toHaveBeenCalledWith(
      expect.objectContaining({ velocity: 20, altitude: 500 }),
    );
  });
});
