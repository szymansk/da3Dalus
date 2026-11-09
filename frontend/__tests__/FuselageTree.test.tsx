/**
 * Tests for fuselage support in AeroplaneTree + PropertyForm (GH#32).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Mocks ──────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    ChevronDown: icon, ChevronRight: icon, Plus: icon, Trash2: icon,
    Eye: icon, EyeOff: icon, Loader: icon, PanelLeftClose: icon, Pencil: icon,
    X: icon, Upload: icon, Check: icon, Loader2: icon, Maximize2: icon,
    Minimize2: icon, Play: icon, Lock: icon, Download: icon, Box: icon,
  };
});

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({ wing: null, isLoading: false, mutate: vi.fn() }),
  useAllWingData: () => ({ wings: [], isLoading: false, error: undefined, mutate: vi.fn() }),
}));

const mockFuselageData = {
  name: "TestFuselage",
  x_secs: [
    { xyz: [0, 0, 0], a: 0.01, b: 0.01, n: 2 },
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

  it("calls selectFuselage on fuselage node click", async () => {
    const user = userEvent.setup();
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["MyFuselage"]}
        aeroplaneName="eHawk"
      />
    );
    await user.click(screen.getByText("MyFuselage"));
    expect(mockSelectFuselage).toHaveBeenCalledWith("MyFuselage");
  });

  it("shows loading when expanded but data not loaded", async () => {
    const user = userEvent.setup();
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
    await user.click(screen.getByText("MyFuselage"));
    expect(screen.getByText(/loading/i)).toBeDefined();
  });

  it("shows xsec nodes with a/b/n details when data loaded", async () => {
    const user = userEvent.setup();
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
    await user.click(screen.getByText("TestFuselage"));

    // 3 xsec nodes visible
    expect(screen.getByText("xsec 0")).toBeDefined();
    expect(screen.getByText("xsec 1")).toBeDefined();
    expect(screen.getByText("xsec 2")).toBeDefined();

    // Details shown
    expect(screen.getByText("a=50.0mm b=40.0mm n=2.3")).toBeDefined();
  });

  it("calls selectFuselageXsec when clicking an xsec", async () => {
    const user = userEvent.setup();
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

    await user.click(screen.getByText("TestFuselage"));
    await user.click(screen.getByText("xsec 1"));

    expect(mockSelectFuselageXsec).toHaveBeenCalledWith(1);
  });

  it("renders both Surface and Solid STEP download links (gh-731)", () => {
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["MyFuselage"]}
        aeroplaneName="eHawk"
      />
    );
    // gh-729: surface STEP icon
    const surface = document.querySelector(
      '[data-testid="download-step-fuselage-MyFuselage"]'
    );
    expect(surface).toBeTruthy();
    expect(surface?.getAttribute("href")).toContain("/fuselages/MyFuselage/step");
    // gh-731: solid STEP icon
    const solid = document.querySelector(
      '[data-testid="download-solid-step-fuselage-MyFuselage"]'
    );
    expect(solid).toBeTruthy();
    expect(solid?.getAttribute("href")).toContain("/fuselages/MyFuselage/solid_step");
    expect(solid?.getAttribute("title")).toContain("Solid");
  });

  it("highlights selected xsec", async () => {
    const user = userEvent.setup();
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

    await user.click(screen.getByText("TestFuselage"));

    // xsec 1 should have selected styling (bg-sidebar-accent + font-semibold)
    const xsec1 = screen.getByText("xsec 1").closest("div");
    expect(xsec1?.className).toContain("font-semibold");
  });
});

describe("Fuselage sections with a contour in AeroplaneTree (gh-1349)", () => {
  it("labels a section with its contour point count", async () => {
    const user = userEvent.setup();
    const contour = [
      [0, -0.04], [0.02, -0.03], [0.04, 0], [0.03, 0.02], [0.02, 0.03], [0.01, 0.035],
      [0.005, 0.039], [0, 0.04],
    ];
    ctxOverrides = { selectedFuselage: "TestFuselage" };
    fuselageReturnValue = {
      fuselage: {
        ...mockFuselageData,
        x_secs: mockFuselageData.x_secs.map((xs) => ({ ...xs, contour })),
      },
    };
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["TestFuselage"]}
        aeroplaneName="eHawk"
      />
    );
    await user.click(screen.getByText("TestFuselage"));
    expect(screen.getByText("a=50.0mm b=40.0mm n=2.3 \u00B7 contour (8 points)")).toBeDefined();
  });
});

describe("Body roles in AeroplaneTree (gh-1355)", () => {
  const bodies = [
    { name: "Haube", role: "canopy" as const, attached_to: "Rumpf" },
    { name: "Rumpf", role: "fuselage" as const, attached_to: null },
    { name: "Gondel", role: "nacelle" as const, attached_to: null },
  ];

  it("lists a canopy under its parent, one level deeper, with its own icon and chip", () => {
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["Haube", "Rumpf", "Gondel"]}
        fuselageBodies={bodies}
        aeroplaneName="eHawk"
      />
    );
    const rows = screen.getAllByRole("treeitem").map((r) => r.textContent ?? "");
    const order = ["Rumpf", "Haube", "Gondel"].map((n) => rows.findIndex((t) => t.includes(n)));
    expect(order).toEqual([...order].sort((a, b) => a - b));

    const canopyRow = screen.getByText("Haube").closest('[role="treeitem"]') as HTMLElement;
    const parentRow = screen.getByText("Rumpf").closest('[role="treeitem"]') as HTMLElement;
    expect(Number.parseInt(canopyRow.style.paddingLeft)).toBeGreaterThan(
      Number.parseInt(parentRow.style.paddingLeft),
    );
    expect(screen.getByText("CANOPY")).toBeDefined();
    expect(screen.getByText("NACELLE")).toBeDefined();
    expect(screen.getByLabelText("canopy")).toBeDefined();
    expect(screen.getByLabelText("nacelle")).toBeDefined();
  });

  it("lists a spinner under the body it sits on, with its own icon and chip (gh-1375)", () => {
    const withSpinner = [...bodies, { name: "Spinner", role: "spinner" as const, attached_to: "Rumpf" }];
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["Spinner", "Haube", "Rumpf", "Gondel"]}
        fuselageBodies={withSpinner}
        aeroplaneName="eHawk"
      />
    );
    const spinnerRow = screen.getByText("Spinner").closest('[role="treeitem"]') as HTMLElement;
    const parentRow = screen.getByText("Rumpf").closest('[role="treeitem"]') as HTMLElement;
    expect(Number.parseInt(spinnerRow.style.paddingLeft)).toBeGreaterThan(
      Number.parseInt(parentRow.style.paddingLeft),
    );
    expect(screen.getByText("SPINNER")).toBeDefined();
    expect(screen.getByLabelText("spinner")).toBeDefined();
  });

  it("shows a body without loaded data as a fuselage", () => {
    render(
      <AeroplaneTree aeroplaneId="aero-1" wingNames={[]} fuselageNames={["X"]} aeroplaneName="eHawk" />
    );
    expect(screen.getByText("FUSELAGE")).toBeDefined();
    expect(screen.getByLabelText("fuselage")).toBeDefined();
  });

  it("opens the body properties from the edit button of a body row", async () => {
    const user = userEvent.setup();
    const onNodeEdit = vi.fn();
    render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={[]}
        fuselageNames={["Rumpf"]}
        fuselageBodies={bodies}
        aeroplaneName="eHawk"
        onNodeEdit={onNodeEdit}
      />
    );
    const row = screen.getByText("Rumpf").closest('[role="treeitem"]') as HTMLElement;
    await user.click(row.querySelector('button[title="Edit"]') as HTMLElement);
    expect(mockSelectFuselage).toHaveBeenCalledWith("Rumpf");
    expect(onNodeEdit).toHaveBeenCalled();
  });
});
