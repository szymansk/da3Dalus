/**
 * Tests for fuselage support in AeroplaneTree + PropertyForm (GH#32).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ── Mocks ──────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    ChevronDown: icon, ChevronRight: icon, Plus: icon, Trash2: icon,
    Eye: icon, EyeOff: icon, Loader: icon, PanelLeftClose: icon, Pencil: icon,
  };
});

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({ wing: null, isLoading: false, mutate: vi.fn() }),
}));

const mockFuselageData = {
  name: "TestFuselage",
  x_secs: [
    { xyz: [0, 0, 0], a: 0.01, b: 0.01, n: 2.0 },
    { xyz: [0.1, 0, 0], a: 0.05, b: 0.04, n: 2.3 },
    { xyz: [0.2, 0, 0], a: 0.03, b: 0.02, n: 2.1 },
  ],
};

let fuselageReturnValue: { fuselage: typeof mockFuselageData | null } = { fuselage: null };
vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => fuselageReturnValue,
}));

const mockSelectFuselage = vi.fn();
const mockSelectFuselageXsec = vi.fn();
const mockSelectWing = vi.fn();

let ctxOverrides: Record<string, unknown> = {};

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: null,
    selectedXsecIndex: null,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
    setAeroplaneId: vi.fn(),
    selectWing: mockSelectWing,
    selectXsec: vi.fn(),
    selectFuselage: mockSelectFuselage,
    selectFuselageXsec: mockSelectFuselageXsec,
    setTreeMode: vi.fn(),
    ...ctxOverrides,
  }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

import { AeroplaneTree } from "@/components/workbench/AeroplaneTree";

beforeEach(() => {
  vi.clearAllMocks();
  fuselageReturnValue = { fuselage: null };
  ctxOverrides = {};
});

// ── Tree Tests ─────────────────────────────────────────────────

describe("Fuselage in AeroplaneTree", () => {
  it("renders fuselage name with FUSELAGE chip", () => {
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["MyFuselage"]}
        aeroplaneName="eHawk"
      />
    );
    // Root is auto-expanded, so fuselage is visible at level 1
    expect(screen.getByText("MyFuselage")).toBeDefined();
    expect(screen.getByText("FUSELAGE")).toBeDefined();
  });

  it("calls selectFuselage on fuselage node click", () => {
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["MyFuselage"]}
        aeroplaneName="eHawk"
      />
    );
    fireEvent.click(screen.getByText("MyFuselage"));
    expect(mockSelectFuselage).toHaveBeenCalledWith("MyFuselage");
  });

  it("shows loading when expanded but data not loaded", () => {
    // selectedFuselage is set (simulating after click)
    ctxOverrides = { selectedFuselage: "MyFuselage" };
    fuselageReturnValue = { fuselage: null };

    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["MyFuselage"]}
        aeroplaneName="eHawk"
      />
    );

    // Click to expand — toggles expandedSet via TreeRow onToggle
    fireEvent.click(screen.getByText("MyFuselage"));
    expect(screen.getByText(/loading/i)).toBeDefined();
  });

  it("shows xsec nodes with a/b/n details when data loaded", () => {
    ctxOverrides = { selectedFuselage: "TestFuselage" };
    fuselageReturnValue = { fuselage: mockFuselageData };

    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["TestFuselage"]}
        aeroplaneName="eHawk"
      />
    );

    // Click to expand
    fireEvent.click(screen.getByText("TestFuselage"));

    // 3 xsec nodes visible
    expect(screen.getByText("xsec 0")).toBeDefined();
    expect(screen.getByText("xsec 1")).toBeDefined();
    expect(screen.getByText("xsec 2")).toBeDefined();

    // Details shown
    expect(screen.getByText("a=50.0mm b=40.0mm n=2.3")).toBeDefined();
  });

  it("calls selectFuselageXsec when clicking an xsec", () => {
    ctxOverrides = { selectedFuselage: "TestFuselage" };
    fuselageReturnValue = { fuselage: mockFuselageData };

    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["TestFuselage"]}
        aeroplaneName="eHawk"
      />
    );

    fireEvent.click(screen.getByText("TestFuselage"));
    fireEvent.click(screen.getByText("xsec 1"));

    expect(mockSelectFuselageXsec).toHaveBeenCalledWith(1);
  });

  it("highlights selected xsec", () => {
    ctxOverrides = {
      selectedFuselage: "TestFuselage",
      selectedFuselageXsecIndex: 1,
    };
    fuselageReturnValue = { fuselage: mockFuselageData };

    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["TestFuselage"]}
        aeroplaneName="eHawk"
      />
    );

    fireEvent.click(screen.getByText("TestFuselage"));

    // xsec 1 should have selected styling (bg-sidebar-accent + font-semibold)
    const xsec1 = screen.getByText("xsec 1").closest("div");
    expect(xsec1?.className).toContain("font-semibold");
  });
});
