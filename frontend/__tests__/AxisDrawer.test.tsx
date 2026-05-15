import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { AxisDrawer } from "@/components/workbench/mission/AxisDrawer";

type MockKpi = {
  axis: string;
  value: number | null;
  unit: string | null;
  score_0_1: number | null;
  range_min: number;
  range_max: number;
  provenance: "computed" | "estimated" | "missing";
  formula: string;
  warning: string | null;
};

let mockKpis: { ist_polygon: Record<string, MockKpi> } | null = {
  ist_polygon: {
    stall_safety: {
      axis: "stall_safety", value: 1.45, unit: "-",
      score_0_1: 0.13, range_min: 1.3, range_max: 2.5,
      provenance: "computed", formula: "V_cruise / V_s1", warning: null,
    },
  },
};

vi.mock("@/hooks/useMissionKpis", () => ({
  useMissionKpis: () => ({
    data: mockKpis,
    isLoading: false,
    error: null,
  }),
}));

describe("AxisDrawer", () => {
  it("renders label, value, formula and provenance", () => {
    mockKpis = {
      ist_polygon: {
        stall_safety: {
          axis: "stall_safety", value: 1.45, unit: "-",
          score_0_1: 0.13, range_min: 1.3, range_max: 2.5,
          provenance: "computed", formula: "V_cruise / V_s1", warning: null,
        },
      },
    };
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={() => undefined} />);
    expect(screen.getByText(/Stall Safety/)).toBeInTheDocument();
    expect(screen.getByText(/1\.450/)).toBeInTheDocument();
    expect(screen.getByText(/V_cruise \/ V_s1/)).toBeInTheDocument();
    expect(screen.getByText(/computed/)).toBeInTheDocument();
    expect(screen.getByText(/13 %/)).toBeInTheDocument();
  });

  it("close button triggers onClose", () => {
    const onClose = vi.fn();
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders an en-dash when value and score are null", () => {
    mockKpis = {
      ist_polygon: {
        stall_safety: {
          axis: "stall_safety", value: null, unit: null,
          score_0_1: null, range_min: 0, range_max: 1,
          provenance: "missing", formula: "n/a", warning: null,
        },
      },
    };
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={() => undefined} />);
    // Both Ist and Score show the en-dash placeholder.
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/missing/)).toBeInTheDocument();
  });

  it("applies the estimated provenance color and renders the warning", () => {
    mockKpis = {
      ist_polygon: {
        glide: {
          axis: "glide", value: 8.2, unit: "-",
          score_0_1: 0.5, range_min: 5, range_max: 15,
          provenance: "estimated", formula: "L/D estimate",
          warning: "polar stale",
        },
      },
    };
    render(<AxisDrawer aeroplaneId="x" axis="glide" onClose={() => undefined} />);
    const prov = screen.getByText(/estimated/);
    expect(prov.className).toContain("text-yellow-400");
    expect(screen.getByText(/polar stale/)).toBeInTheDocument();
  });

  it("renders nothing when KPIs are not loaded", () => {
    mockKpis = null;
    const { container } = render(
      <AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the requested axis is missing", () => {
    mockKpis = { ist_polygon: {} };
    const { container } = render(
      <AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
