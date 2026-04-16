/**
 * Regression tests for /workbench/components page.
 *
 * These tests guard against gh#57-fav: the "+ New Component" button silently
 * did nothing because <ComponentEditDialog/> was passed as a third child of
 * <WorkbenchTwoPanel/>, which drops any child beyond the first two.
 *
 * If you touch the ComponentsPage layout, keep the dialog rendered OUTSIDE
 * the WorkbenchTwoPanel (e.g. as a sibling via Fragment or via a portal).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Package: icon, Search: icon, Plus: icon, Settings: icon, Trash2: icon,
    X: icon, Loader2: icon, ChevronDown: icon, ChevronRight: icon,
    Box: icon, Lock: icon, Unlock: icon, Upload: icon,
    FolderPlus: icon, Check: icon, GripVertical: icon,
  };
});

// Stub SWR-backed hooks so the page can render without a real backend.
vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({
    components: [],
    total: 0,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  useComponentTypes: () => ["generic", "servo", "battery"],
  createComponent: vi.fn().mockResolvedValue({}),
  updateComponent: vi.fn().mockResolvedValue({}),
  deleteComponent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/hooks/useComponentTree", () => ({
  useComponentTree: () => ({
    tree: [],
    totalNodes: 0,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  addTreeNode: vi.fn().mockResolvedValue({}),
  deleteTreeNode: vi.fn().mockResolvedValue(undefined),
  moveTreeNode: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/hooks/useConstructionParts", () => ({
  useConstructionParts: () => ({
    parts: [],
    total: 0,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  uploadConstructionPart: vi.fn().mockResolvedValue({}),
  deleteConstructionPart: vi.fn().mockResolvedValue(undefined),
  updateConstructionPart: vi.fn().mockResolvedValue({}),
  lockConstructionPart: vi.fn().mockResolvedValue({}),
  unlockConstructionPart: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: null,
    selectedXsecIndex: null,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
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

import ComponentsPage from "@/app/workbench/components/page";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ComponentsPage — '+ New Component' dialog", () => {
  it("renders the '+ New Component' button", () => {
    render(<ComponentsPage />);
    expect(screen.getByText("New Component")).toBeDefined();
  });

  it("does not render the dialog until the button is clicked", () => {
    render(<ComponentsPage />);
    // Dialog heading only exists when the dialog is open.
    expect(screen.queryByText("New Component", { selector: "span" })).toBeNull();
  });

  it("opens the create dialog when '+ New Component' is clicked", () => {
    render(<ComponentsPage />);

    const button = screen.getByText("New Component");
    fireEvent.click(button);

    // The dialog title is "New Component" inside a <span> — same text as the
    // button, so we assert on the presence of dialog-only form labels instead.
    expect(screen.getByText("Name *")).toBeDefined();
    expect(screen.getByText("Manufacturer")).toBeDefined();
    expect(screen.getByText("Description")).toBeDefined();
  });

  it("closes the dialog when Cancel is clicked", () => {
    render(<ComponentsPage />);

    fireEvent.click(screen.getByText("New Component"));
    expect(screen.getByText("Name *")).toBeDefined();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("Name *")).toBeNull();
  });
});
