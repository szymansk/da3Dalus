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

  it("shows drilldown placeholder toast after onAxisClick is invoked", () => {
    aeroplaneId = "aero-1";
    render(<MissionPage />);
    act(() => {
      fireEvent.click(screen.getByText(/compliance-stub/));
    });
    expect(screen.getByText(/Axis drilldown for/)).toBeInTheDocument();
    expect(screen.getByText(/climb/)).toBeInTheDocument();
    expect(screen.getByText(/coming in Phase 7/)).toBeInTheDocument();
  });

  it("closes the drilldown toast when × is clicked", () => {
    aeroplaneId = "aero-1";
    render(<MissionPage />);
    act(() => {
      fireEvent.click(screen.getByText(/compliance-stub/));
    });
    expect(screen.getByText(/Axis drilldown for/)).toBeInTheDocument();
    act(() => {
      fireEvent.click(
        screen.getByRole("button", { name: /Close drilldown placeholder/ }),
      );
    });
    expect(screen.queryByText(/Axis drilldown for/)).not.toBeInTheDocument();
  });
});
