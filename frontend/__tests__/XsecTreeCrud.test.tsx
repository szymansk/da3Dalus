/**
 * Tests for X-Secs tree CRUD controls in ASB mode (GH#358).
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
    Minimize2: icon, Play: icon, Lock: icon,
  };
});

const mockWing = {
  name: "TestWing",
  symmetric: false,
  design_model: "asb" as const,
  x_secs: [
    { xyz_le: [0, 0, 0], chord: 0.2, twist: 0, airfoil: "naca0012" },
    { xyz_le: [0, 0.5, 0], chord: 0.15, twist: -2, airfoil: "naca0012" },
    { xyz_le: [0, 1.0, 0], chord: 0.1, twist: -4, airfoil: "naca0012" },
  ],
};

vi.mock("@/hooks/useWings", () => ({
  useWing: () => ({ wing: mockWing, isLoading: false, mutate: vi.fn() }),
  useAllWingData: () => ({ wings: [mockWing], isLoading: false, error: undefined, mutate: vi.fn() }),
}));

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({ wingConfig: null }),
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: "TestWing",
    selectedXsecIndex: null,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "asb",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: vi.fn(),
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

vi.mock("@/hooks/useFuselage", () => ({
  useFuselage: () => ({ fuselage: null, mutate: vi.fn() }),
}));

vi.mock("@/hooks/useFuselages", () => ({
  useFuselages: () => ({ fuselageNames: [], mutate: vi.fn() }),
}));

import { AeroplaneTree } from "@/components/workbench/AeroplaneTree";

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────

describe("X-Secs tree CRUD controls (ASB mode)", () => {
  function renderTree() {
    return render(
      <AeroplaneTree
        aeroplaneId="aero-1"
        wingNames={["TestWing"]}
        fuselageNames={[]}
        aeroplaneName="eHawk"
      />,
    );
  }

  it("renders insert points between consecutive x-secs", () => {
    renderTree();
    // With 3 x-secs there should be 2 insert points (between 0-1 and 1-2)
    const insertButtons = screen.getAllByText("insert");
    expect(insertButtons).toHaveLength(2);
  });

  it("clicking insert point calls handleInsertXsec", async () => {
    const user = userEvent.setup();
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    renderTree();
    const insertButtons = screen.getAllByText("insert");
    await user.click(insertButtons[0]);

    // Insert at index 1 (between x_sec 0 and x_sec 1)
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/aeroplanes/aero-1/wings/TestWing/cross_sections/1",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders + x_sec button after last x-sec", () => {
    renderTree();
    expect(screen.getByText("+ x_sec")).toBeDefined();
  });

  it("clicking + x_sec calls handleAddSegment", async () => {
    const user = userEvent.setup();
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    renderTree();
    await user.click(screen.getByText("+ x_sec"));

    // Append at index equal to x_secs.length (3)
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/aeroplanes/aero-1/wings/TestWing/cross_sections/3",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("wing node has delete action", async () => {
    const user = userEvent.setup();
    const mockConfirm = vi.fn().mockReturnValue(true);
    global.confirm = mockConfirm;
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    renderTree();
    // The wing node "TestWing" should have a Trash2 button (rendered as span with onClick)
    // Find the tree row containing "TestWing" and click the delete button within it
    const wingNode = screen.getByText("TestWing");
    const wingRow = wingNode.closest("[role='treeitem']")!;
    // The delete button is the last button with stopPropagation in the row
    const deleteBtn = wingRow.querySelector("button:last-of-type")!;
    await user.click(deleteBtn);

    expect(mockConfirm).toHaveBeenCalledWith('Delete wing "TestWing"?');
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/aeroplanes/aero-1/wings/TestWing",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("no insert point before first x-sec", () => {
    renderTree();
    // Only 2 insert nodes exist (not 3) — none before index 0
    const insertButtons = screen.getAllByText("insert");
    expect(insertButtons).toHaveLength(2);
  });
});
