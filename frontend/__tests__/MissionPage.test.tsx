import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";

let aeroplaneId: string | null = null;
const openPicker = vi.fn();

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({ aeroplaneId, hydrated: true, openPicker }),
}));

vi.mock("@/components/workbench/mission/MissionCompliancePanel", () => ({
  MissionCompliancePanel: ({
    onAxisClick,
  }: {
    onAxisClick: (a: string) => void;
  }) => (
    <button type="button" onClick={() => onAxisClick("climb")}>
      compliance-stub
    </button>
  ),
}));

vi.mock("@/components/workbench/mission/MissionObjectivesPanel", () => ({
  MissionObjectivesPanel: () => <div>objectives-stub</div>,
}));

vi.mock("@/components/workbench/WorkbenchTwoPanel", () => ({
  WorkbenchTwoPanel: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock("@/components/workbench/mission/AxisDrawer", () => ({
  AxisDrawer: ({ axis, onClose }: { axis: string; onClose: () => void }) => (
    <div data-testid="axis-drawer">
      drawer-axis-{axis}
      <button type="button" onClick={onClose}>close-drawer</button>
    </div>
  ),
}));

import MissionPage from "@/app/workbench/mission/page";

describe("MissionPage", () => {
  beforeEach(() => {
    openPicker.mockClear();
  });

  it("prompts to select an aeroplane when none is set", () => {
    aeroplaneId = null;
    render(<MissionPage />);
    expect(
      screen.getByText(/Select an aeroplane to view Mission compliance/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Select an aeroplane to edit its Mission objectives/),
    ).toBeInTheDocument();
  });

  it("calls openPicker when hydrated with no aeroplaneId", () => {
    aeroplaneId = null;
    render(<MissionPage />);
    expect(openPicker).toHaveBeenCalledTimes(1);
  });

  it("renders both panels when an aeroplane is selected", () => {
    aeroplaneId = "aero-1";
    render(<MissionPage />);
    expect(screen.getByText(/compliance-stub/)).toBeInTheDocument();
    expect(screen.getByText(/objectives-stub/)).toBeInTheDocument();
  });

  it("shows AxisDrawer after onAxisClick is invoked", () => {
    aeroplaneId = "aero-1";
    render(<MissionPage />);
    act(() => {
      fireEvent.click(screen.getByText(/compliance-stub/));
    });
    expect(screen.getByTestId("axis-drawer")).toHaveTextContent("drawer-axis-climb");
  });

  it("closes the AxisDrawer when its close button is clicked", () => {
    aeroplaneId = "aero-1";
    render(<MissionPage />);
    act(() => {
      fireEvent.click(screen.getByText(/compliance-stub/));
    });
    expect(screen.getByTestId("axis-drawer")).toBeInTheDocument();
    act(() => {
      fireEvent.click(screen.getByText("close-drawer"));
    });
    expect(screen.queryByTestId("axis-drawer")).toBeNull();
  });
});
