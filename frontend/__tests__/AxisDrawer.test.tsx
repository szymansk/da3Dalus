import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { AxisDrawer } from "@/components/workbench/mission/AxisDrawer";

vi.mock("@/hooks/useMissionKpis", () => ({
  useMissionKpis: () => ({
    data: {
      aeroplane_uuid: "x",
      ist_polygon: {
        stall_safety: {
          axis: "stall_safety", value: 1.45, unit: "-",
          score_0_1: 0.13, range_min: 1.3, range_max: 2.5,
          provenance: "computed", formula: "V_cruise / V_s1", warning: null,
        },
      },
      target_polygons: [],
      active_mission_id: "trainer",
      computed_at: "now",
      context_hash: "h",
    },
    isLoading: false, error: null,
  }),
}));

describe("AxisDrawer", () => {
  it("renders label, value, formula and provenance", () => {
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={() => undefined} />);
    expect(screen.getByText(/Stall Safety/)).toBeInTheDocument();
    expect(screen.getByText(/1\.450/)).toBeInTheDocument();
    expect(screen.getByText(/V_cruise \/ V_s1/)).toBeInTheDocument();
    expect(screen.getByText(/computed/)).toBeInTheDocument();
  });

  it("close button triggers onClose", () => {
    const onClose = vi.fn();
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
