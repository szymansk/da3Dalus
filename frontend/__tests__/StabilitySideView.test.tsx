import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { StabilityData } from "@/hooks/useStability";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon };
});

import React from "react";
import { StabilitySideView } from "@/components/workbench/StabilitySideView";

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

describe("StabilitySideView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Plotly container div", () => {
    const { container } = render(<StabilitySideView data={FAKE_DATA} />);
    const plotDiv = container.querySelector("[data-testid='stability-plot']");
    expect(plotDiv).toBeInTheDocument();
  });

  it("renders KPI badges for static margin and stability class", () => {
    render(<StabilitySideView data={FAKE_DATA} />);
    expect(screen.getByText(/33\.3%/)).toBeInTheDocument();
    expect(screen.getByText(/stable/i)).toBeInTheDocument();
  });

  it("shows DIRTY badge when status is DIRTY", () => {
    const dirtyData = { ...FAKE_DATA, status: "DIRTY" as const };
    render(<StabilitySideView data={dirtyData} />);
    expect(screen.getByText(/outdated/i)).toBeInTheDocument();
  });

  it("renders derivative badges for Cma, Cnb, Clb", () => {
    render(<StabilitySideView data={FAKE_DATA} />);
    expect(screen.getByText(/Cm.α/)).toBeInTheDocument();
    expect(screen.getByText(/Cn.β/)).toBeInTheDocument();
    expect(screen.getByText(/Cl.β/)).toBeInTheDocument();
  });
});
