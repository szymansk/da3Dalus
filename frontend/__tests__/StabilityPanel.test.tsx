import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { StabilityData } from "@/hooks/useStability";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon };
});

vi.mock("@/components/workbench/StabilitySideView", () => ({
  StabilitySideView: ({ data }: { data: StabilityData }) =>
    React.createElement("div", { "data-testid": "side-view" }, data.stability_class),
}));

import { StabilityPanel } from "@/components/workbench/StabilityPanel";

const FAKE_DATA: StabilityData = {
  id: 1,
  aeroplane_id: 42,
  solver: "avl",
  neutral_point_x: 0.25,
  mac: 0.15,
  cg_x_used: 0.20,
  static_margin_pct: 33.3,
  stability_class: "stable",
  cg_range_forward: 0.17,
  cg_range_aft: 0.24,
  Cma: -1.2,
  Cnb: 0.05,
  Clb: -0.03,
  is_statically_stable: true,
  is_directionally_stable: true,
  is_laterally_stable: true,
  trim_alpha_deg: 2.5,
  trim_elevator_deg: -3.0,
  computed_at: "2026-05-08T12:00:00Z",
  status: "CURRENT",
  geometry_hash: "abc123",
};

describe("StabilityPanel", () => {
  it("shows empty state when data is null", () => {
    render(
      <StabilityPanel data={null} isComputing={false} error={null} onCompute={vi.fn()} />,
    );
    expect(screen.getByText(/no stability data/i)).toBeInTheDocument();
  });

  it("shows computing spinner when isComputing and no data", () => {
    render(
      <StabilityPanel data={null} isComputing={true} error={null} onCompute={vi.fn()} />,
    );
    expect(screen.getByText(/computing/i)).toBeInTheDocument();
  });

  it("shows error banner when error is set", () => {
    render(
      <StabilityPanel data={null} isComputing={false} error="Server error" onCompute={vi.fn()} />,
    );
    expect(screen.getByText("Server error")).toBeInTheDocument();
  });

  it("renders StabilitySideView when data is present", () => {
    render(
      <StabilityPanel data={FAKE_DATA} isComputing={false} error={null} onCompute={vi.fn()} />,
    );
    expect(screen.getByTestId("side-view")).toBeInTheDocument();
  });

  it("calls onCompute when Compute Stability button is clicked", async () => {
    const onCompute = vi.fn();
    const user = userEvent.setup();
    render(
      <StabilityPanel data={null} isComputing={false} error={null} onCompute={onCompute} />,
    );
    await user.click(screen.getByRole("button", { name: /compute stability/i }));
    expect(onCompute).toHaveBeenCalledOnce();
  });

  it("disables compute button when isComputing", () => {
    render(
      <StabilityPanel data={FAKE_DATA} isComputing={true} error={null} onCompute={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /computing/i })).toBeDisabled();
  });
});
