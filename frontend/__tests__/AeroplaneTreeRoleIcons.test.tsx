/**
 * Tests for AeroplaneTree role icons and pitch control surface warning (gh-450).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import type { XSec } from "@/hooks/useWings";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", async (importOriginal) => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    ...(await importOriginal<Record<string, unknown>>()),
    ChevronDown: icon,
    ChevronRight: icon,
    Plus: icon,
    Trash2: icon,
    Eye: icon,
    EyeOff: icon,
    Loader: icon,
    PanelLeftClose: icon,
    Pencil: icon,
    X: icon,
    Check: icon,
    ChevronUp: icon,
    Search: icon,
    AlertTriangle: icon,
    Scale: icon,
    GripVertical: icon,
  };
});

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8001/v2",
}));

const mockSelectWing = vi.fn();
const mockSelectXsec = vi.fn();
const mockSelectFuselage = vi.fn();
const mockSelectFuselageXsec = vi.fn();
const mockSetTreeMode = vi.fn();

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    selectedWing: "Main Wing",
    selectedXsecIndex: 0,
    selectWing: mockSelectWing,
    selectXsec: mockSelectXsec,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    selectFuselage: mockSelectFuselage,
    selectFuselageXsec: mockSelectFuselageXsec,
    treeMode: "wingconfig",
    setTreeMode: mockSetTreeMode,
  }),
}));

let mockWingData: { name: string; symmetric: boolean; x_secs: XSec[]; design_model?: string } | null = null;

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({
    wing: mockWingData,
    isLoading: false,
    mutate: vi.fn(),
  }),
}));

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({ wingConfig: { nose_pnt: [0, 0, 0] } }),
}));

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({ fuselage: null, mutate: vi.fn() }),
}));

vi.mock("@/hooks/useFuselages", () => ({
  useFuselages: () => ({ mutate: vi.fn() }),
}));

vi.mock("@/components/workbench/ImportFuselageDialog", () => ({
  ImportFuselageDialog: () => null,
}));

vi.mock("@/components/workbench/CreateWingDialog", () => ({
  CreateWingDialog: () => null,
}));

import { AeroplaneTree } from "@/components/workbench/AeroplaneTree";

// ── Helpers ───────────────────────────────────────────────────────

function makeXsec(overrides: Partial<XSec> = {}): XSec {
  return {
    xyz_le: [0, 0, 0],
    chord: 0.2,
    twist: 0,
    airfoil: "naca0012",
    ...overrides,
  };
}

function makeWing(xsecs: XSec[]) {
  return {
    name: "Main Wing",
    symmetric: true,
    x_secs: xsecs,
    design_model: "wc",
  };
}

const baseProps = {
  aeroplaneId: "1",
  wingNames: ["Main Wing"],
  aeroplaneName: "Test Plane",
};

// ── Tests ─────────────────────────────────────────────────────────

describe("AeroplaneTree role icons (gh-450)", () => {
  it("shows role icon in segment chip for elevator TED", () => {
    mockWingData = makeWing([
      makeXsec({ trailing_edge_device: { role: "elevator", label: "" } }),
      makeXsec(),
    ]);
    render(<AeroplaneTree {...baseProps} />);
    expect(screen.getByText("↕ ELEVATOR")).toBeTruthy();
  });

  it("shows role icon in segment chip for aileron TED with custom label", () => {
    mockWingData = makeWing([
      makeXsec({ trailing_edge_device: { role: "aileron", label: "Left Aileron" } }),
      makeXsec(),
    ]);
    render(<AeroplaneTree {...baseProps} />);
    expect(screen.getByText("↔ AILERON")).toBeTruthy();
  });

  it("shows correct role icon for each role type in segment chip", () => {
    const roles = [
      { role: "elevator", icon: "↕" },
      { role: "aileron", icon: "↔" },
      { role: "rudder", icon: "⟳" },
      { role: "elevon", icon: "⤡" },
      { role: "stabilator", icon: "↕" },
      { role: "flap", icon: "▽" },
      { role: "spoiler", icon: "▢" },
      { role: "other", icon: "○" },
    ];
    for (const { role, icon } of roles) {
      mockWingData = makeWing([
        makeXsec({ trailing_edge_device: { role, label: "" } }),
        makeXsec(),
      ]);
      const { unmount } = render(<AeroplaneTree {...baseProps} />);
      expect(screen.getByText(`${icon} ${role.toUpperCase()}`)).toBeTruthy();
      unmount();
    }
  });
});

describe("AeroplaneTree pitch warning (gh-450)", () => {
  it("shows warning when wing has no pitch control surface", () => {
    mockWingData = makeWing([
      makeXsec({ trailing_edge_device: { role: "aileron", label: "" } }),
      makeXsec(),
    ]);
    render(<AeroplaneTree {...baseProps} />);
    expect(
      screen.getByText(/No pitch control surface assigned/),
    ).toBeTruthy();
  });

  it("shows warning when wing has no TEDs at all", () => {
    mockWingData = makeWing([makeXsec(), makeXsec()]);
    render(<AeroplaneTree {...baseProps} />);
    expect(
      screen.getByText(/No pitch control surface assigned/),
    ).toBeTruthy();
  });

  it("does not show warning when wing has elevator", () => {
    mockWingData = makeWing([
      makeXsec({ trailing_edge_device: { role: "elevator", label: "" } }),
      makeXsec(),
    ]);
    render(<AeroplaneTree {...baseProps} />);
    expect(
      screen.queryByText(/No pitch control surface assigned/),
    ).toBeNull();
  });

  it("does not show warning when wing has elevon", () => {
    mockWingData = makeWing([
      makeXsec({ trailing_edge_device: { role: "elevon", label: "" } }),
      makeXsec(),
    ]);
    render(<AeroplaneTree {...baseProps} />);
    expect(
      screen.queryByText(/No pitch control surface assigned/),
    ).toBeNull();
  });

  it("does not show warning when wing has stabilator", () => {
    mockWingData = makeWing([
      makeXsec({ trailing_edge_device: { role: "stabilator", label: "" } }),
      makeXsec(),
    ]);
    render(<AeroplaneTree {...baseProps} />);
    expect(
      screen.queryByText(/No pitch control surface assigned/),
    ).toBeNull();
  });

  it("does not show warning when no wing is loaded", () => {
    mockWingData = null;
    render(<AeroplaneTree {...baseProps} />);
    expect(
      screen.queryByText(/No pitch control surface assigned/),
    ).toBeNull();
  });
});
