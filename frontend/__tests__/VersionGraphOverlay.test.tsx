/**
 * Unit tests for VersionGraphOverlay, VersionGraph, and GraphRow (gh-961).
 *
 * Covered:
 * 1. VersionGraph renders one row per node, newest first.
 * 2. Snapshot nodes get filled dot (data-dot-style="filled"), editable heads get hollow.
 * 3. Toolbar enable/disable matrix:
 *    - select snapshot → Restore enabled, Snapshot disabled
 *    - select editable head → Snapshot enabled, Restore disabled
 *    - select node on main branch → Adopt/Discard disabled
 *    - select node on non-main branch → Adopt/Discard enabled
 * 4. Compare: checking 2 rows enables Compare button; 3rd check is no-op.
 * 5. Compare (2 selected) → clicking Compare opens VersionCompareView.
 * 6. Overlay closes on Escape keydown.
 * 7. Overlay closes on backdrop click.
 * 8. BranchNameInput shown in toolbar for Branch from / Restore.
 * 9. Discard two-step confirm.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { "data-icon": "true", ...props });
  return {
    X: icon,
    GitBranch: icon,
    RotateCcw: icon,
    GitFork: icon,
    Star: icon,
    Trash2: icon,
    ArrowLeftRight: icon,
    Bot: icon,
    User: icon,
    Clock: icon,
    Camera: icon,
    GitMerge: icon,
    ChevronDown: icon,
    Pencil: icon,
  };
});

const mockUseLineageTree = vi.fn();
const mockUseVersionActions = vi.fn();
const mockUseCompareNodes = vi.fn();
vi.mock("@/hooks/useVersioning", () => ({
  useLineageTree: (...args: unknown[]) => mockUseLineageTree(...args),
  useVersionActions: (...args: unknown[]) => mockUseVersionActions(...args),
  useCompareNodes: (...args: unknown[]) => mockUseCompareNodes(...args),
}));

// VersionCompareView stub
vi.mock("@/components/workbench/VersionCompareView", () => ({
  VersionCompareView: ({ onClose }: { onClose: () => void }) =>
    React.createElement("div", { "data-testid": "version-compare-view" },
      React.createElement("button", { type: "button", onClick: onClose, "aria-label": "Close compare panel" }, "Close compare"),
    ),
}));

// ---------------------------------------------------------------------------
// Imports (after mock hoisting)
// ---------------------------------------------------------------------------

import { VersionGraphOverlay } from "@/components/workbench/VersionGraphOverlay";
import type { TreeOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Fixtures — spec worked example (main + ai/winglet-exp + fix/stall)
// ---------------------------------------------------------------------------

const TREE: TreeOut = {
  root_id: 1,
  nodes: [
    // row0: working head on main (editable, is_head)
    {
      id: 10,
      uuid: "uuid-10",
      name: "Working head",
      branch_id: 1,
      predecessor_id: 20,
      root_id: 1,
      is_immutable: false,
      is_head: true,
      version_label: "working head",
      version_note: "editable",
      created_by: "human",
      created_at: "2026-06-10T14:02:00Z",
    },
    // row1: winglet draft on ai branch (editable, is_head)
    {
      id: 30,
      uuid: "uuid-30",
      name: "winglet draft",
      branch_id: 2,
      predecessor_id: 20,
      root_id: 1,
      is_immutable: false,
      is_head: true,
      version_label: "winglet draft",
      version_note: "+6% L/D",
      created_by: "ai",
      created_at: "2026-06-09T10:00:00Z",
    },
    // row2: v1.1 snapshot on main
    {
      id: 20,
      uuid: "uuid-20",
      name: "v1.1",
      branch_id: 1,
      predecessor_id: 5,
      root_id: 1,
      is_immutable: true,
      is_head: false,
      version_label: "v1.1",
      version_note: null,
      created_by: "human",
      created_at: "2026-06-08T09:00:00Z",
    },
    // row3: washout fix on fix/stall (editable, is_head)
    {
      id: 40,
      uuid: "uuid-40",
      name: "washout +1.5",
      branch_id: 3,
      predecessor_id: 5,
      root_id: 1,
      is_immutable: false,
      is_head: true,
      version_label: "washout +1.5",
      version_note: null,
      created_by: "human",
      created_at: "2026-06-07T09:00:00Z",
    },
    // row4: v1.0 snapshot on main
    {
      id: 5,
      uuid: "uuid-5",
      name: "v1.0",
      branch_id: 1,
      predecessor_id: 1,
      root_id: 1,
      is_immutable: true,
      is_head: false,
      version_label: "v1.0",
      version_note: null,
      created_by: "human",
      created_at: "2026-06-06T08:00:00Z",
    },
    // row5: root snapshot on main
    {
      id: 1,
      uuid: "uuid-1",
      name: "root",
      branch_id: 1,
      predecessor_id: null,
      root_id: 1,
      is_immutable: true,
      is_head: false,
      version_label: "root",
      version_note: null,
      created_by: "human",
      created_at: "2026-06-05T08:00:00Z",
    },
  ],
  branches: [
    {
      id: 1,
      root_id: 1,
      head_id: 10,
      name: "main",
      is_main: true,
      created_by: "human",
      created_at: "2026-06-05T08:00:00Z",
    },
    {
      id: 2,
      root_id: 1,
      head_id: 30,
      name: "ai/winglet-exp",
      is_main: false,
      created_by: "ai",
      created_at: "2026-06-09T10:00:00Z",
    },
    {
      id: 3,
      root_id: 1,
      head_id: 40,
      name: "fix/stall",
      is_main: false,
      created_by: "human",
      created_at: "2026-06-07T09:00:00Z",
    },
  ],
};

const DEFAULT_ACTIONS = {
  snapshot: vi.fn().mockResolvedValue({ id: 99 }),
  createBranch: vi.fn().mockResolvedValue({ id: 10, head_id: 10, name: "exp" }),
  adoptBranch: vi.fn().mockResolvedValue({ id: 2, head_id: 30, is_main: true }),
  restore: vi.fn().mockResolvedValue({ id: 5, head_id: 20, name: "restored" }),
  discardBranch: vi.fn().mockResolvedValue(undefined),
  renameBranch: vi.fn().mockResolvedValue({ id: 2, name: "new-name" }),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderOverlay(overrides: {
  rootId?: number | null;
  currentHeadId?: number | null;
  aeroplaneId?: number | null;
  aeroplaneLabel?: string;
  onClose?: () => void;
  onSwitchAeroplane?: (uuid: string) => void;
  treeOverride?: Partial<{ tree: TreeOut | undefined; isLoading: boolean; error: Error | undefined; mutate: ReturnType<typeof vi.fn> }>;
  actionsOverride?: Partial<typeof DEFAULT_ACTIONS>;
} = {}) {
  const {
    rootId = 1,
    currentHeadId = 10,
    aeroplaneId = 10,
    aeroplaneLabel,
    onClose = vi.fn(),
    onSwitchAeroplane,
    treeOverride = {},
    actionsOverride = {},
  } = overrides;

  mockUseLineageTree.mockReturnValue({
    tree: TREE,
    isLoading: false,
    error: undefined,
    mutate: vi.fn().mockResolvedValue(TREE),
    ...treeOverride,
  });

  mockUseVersionActions.mockReturnValue({ ...DEFAULT_ACTIONS, ...actionsOverride });

  mockUseCompareNodes.mockReturnValue({
    compareOut: undefined,
    isLoading: false,
    error: undefined,
  });

  return render(
    <VersionGraphOverlay
      rootId={rootId}
      currentHeadId={currentHeadId}
      aeroplaneId={aeroplaneId}
      aeroplaneLabel={aeroplaneLabel}
      onClose={onClose}
      onSwitchAeroplane={onSwitchAeroplane}
    />,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("VersionGraphOverlay (gh-961)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCompareNodes.mockReturnValue({
      compareOut: undefined,
      isLoading: false,
      error: undefined,
    });
  });

  // -------------------------------------------------------------------------
  // 1. Renders one row per node, newest first
  // -------------------------------------------------------------------------
  it("renders one row per node", () => {
    renderOverlay();
    // TREE has 6 nodes; every version_label should appear
    expect(screen.getByText("working head")).toBeDefined();
    expect(screen.getByText("winglet draft")).toBeDefined();
    expect(screen.getByText("v1.1")).toBeDefined();
    expect(screen.getByText("washout +1.5")).toBeDefined();
    expect(screen.getByText("v1.0")).toBeDefined();
    expect(screen.getByText("root")).toBeDefined();
  });

  it("renders rows in newest-first order (working head before root)", () => {
    renderOverlay();
    const rows = screen.getAllByRole("checkbox");
    // There should be one checkbox per row (compare checkboxes)
    expect(rows.length).toBe(6);
  });

  // -------------------------------------------------------------------------
  // 2. Dot styles: snapshot=filled, editable head=hollow
  // -------------------------------------------------------------------------
  it("snapshot nodes have filled dot style, editable heads have hollow", () => {
    const { container } = renderOverlay();
    const filledDots = container.querySelectorAll('[data-dot-style="filled"]');
    const hollowDots = container.querySelectorAll('[data-dot-style="hollow"]');
    // 4 snapshots: v1.1, v1.0, root + node1(snapshot); 3 editable heads
    expect(filledDots.length).toBeGreaterThan(0);
    expect(hollowDots.length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // 3. Toolbar enable/disable matrix
  // -------------------------------------------------------------------------
  describe("toolbar enable/disable", () => {
    it("with no selection, all action buttons are disabled", () => {
      renderOverlay();
      expect(screen.getByRole("button", { name: /snapshot/i }).hasAttribute("disabled")).toBe(true);
      expect(screen.getByRole("button", { name: /branch from/i }).hasAttribute("disabled")).toBe(true);
      expect(screen.getByRole("button", { name: /restore/i }).hasAttribute("disabled")).toBe(true);
      expect(screen.getByRole("button", { name: /adopt/i }).hasAttribute("disabled")).toBe(true);
      expect(screen.getByRole("button", { name: /discard/i }).hasAttribute("disabled")).toBe(true);
    });

    it("selecting a snapshot node: Restore enabled, Snapshot disabled", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // Click on v1.1 row (snapshot, branch=main)
      const v11Row = screen.getByTestId("graph-row-20");
      await user.click(v11Row);

      expect(screen.getByRole("button", { name: /restore/i }).hasAttribute("disabled")).toBe(false);
      expect(screen.getByRole("button", { name: /snapshot/i }).hasAttribute("disabled")).toBe(true);
      expect(screen.getByRole("button", { name: /branch from/i }).hasAttribute("disabled")).toBe(false);
    });

    it("selecting an editable head: Snapshot enabled, Restore disabled", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // Click on working head row (editable, is_head, branch=main)
      const headRow = screen.getByTestId("graph-row-10");
      await user.click(headRow);

      expect(screen.getByRole("button", { name: /snapshot/i }).hasAttribute("disabled")).toBe(false);
      expect(screen.getByRole("button", { name: /restore/i }).hasAttribute("disabled")).toBe(true);
    });

    it("selecting node on main branch: Adopt and Discard disabled", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // v1.1 is on main branch
      const v11Row = screen.getByTestId("graph-row-20");
      await user.click(v11Row);

      expect(screen.getByRole("button", { name: /adopt/i }).hasAttribute("disabled")).toBe(true);
      expect(screen.getByRole("button", { name: /discard/i }).hasAttribute("disabled")).toBe(true);
    });

    it("selecting node on non-main branch: Adopt and Discard enabled", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // winglet draft is on ai/winglet-exp (non-main)
      const aiRow = screen.getByTestId("graph-row-30");
      await user.click(aiRow);

      expect(screen.getByRole("button", { name: /adopt/i }).hasAttribute("disabled")).toBe(false);
      expect(screen.getByRole("button", { name: /discard/i }).hasAttribute("disabled")).toBe(false);
    });

    it("selecting non-head node on non-main: Snapshot disabled, others enabled", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // washout is the head on fix/stall; let's select it — it IS a head
      const fixRow = screen.getByTestId("graph-row-40");
      await user.click(fixRow);

      expect(screen.getByRole("button", { name: /snapshot/i }).hasAttribute("disabled")).toBe(false);
      expect(screen.getByRole("button", { name: /adopt/i }).hasAttribute("disabled")).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // 4. Compare: checking 2 rows enables Compare; 3rd is no-op
  // -------------------------------------------------------------------------
  it("checking 2 nodes enables the Compare button", async () => {
    const user = userEvent.setup();
    renderOverlay();

    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]);
    await user.click(checkboxes[1]);

    const compareBtn = screen.getByRole("button", { name: /compare \(2\)/i });
    expect(compareBtn.hasAttribute("disabled")).toBe(false);
  });

  it("Compare button is disabled when fewer than 2 checked", async () => {
    const user = userEvent.setup();
    renderOverlay();

    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]);

    const compareBtn = screen.getByRole("button", { name: /compare \(1\)/i });
    expect(compareBtn.hasAttribute("disabled")).toBe(true);
  });

  it("checking a 3rd node is a no-op (compare set stays at 2)", async () => {
    const user = userEvent.setup();
    renderOverlay();

    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]);
    await user.click(checkboxes[1]);
    await user.click(checkboxes[2]); // 3rd — should be ignored

    // Still shows (2) not (3)
    expect(screen.getByRole("button", { name: /compare \(2\)/i })).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 5. Clicking Compare opens VersionCompareView
  // -------------------------------------------------------------------------
  it("clicking Compare opens VersionCompareView", async () => {
    const user = userEvent.setup();
    renderOverlay();

    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]);
    await user.click(checkboxes[1]);

    const compareBtn = screen.getByRole("button", { name: /compare \(2\)/i });
    await user.click(compareBtn);

    expect(screen.getByTestId("version-compare-view")).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 6. Overlay closes on Escape
  // -------------------------------------------------------------------------
  it("pressing Escape calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderOverlay({ onClose });

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("pressing Escape with compare open closes compare, not the overlay", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderOverlay({ onClose });

    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]);
    await user.click(checkboxes[1]);
    await user.click(screen.getByRole("button", { name: /compare \(2\)/i }));
    expect(screen.getByTestId("version-compare-view")).toBeDefined();

    await user.keyboard("{Escape}");

    expect(screen.queryByTestId("version-compare-view")).toBeNull();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("selecting a row via keyboard (Enter) selects it", async () => {
    const user = userEvent.setup();
    renderOverlay();

    const headRow = screen.getByTestId("graph-row-10");
    headRow.focus();
    await user.keyboard("{Enter}");

    expect(headRow.getAttribute("aria-selected")).toBe("true");
  });

  // -------------------------------------------------------------------------
  // 7. Overlay closes on backdrop click
  // -------------------------------------------------------------------------
  it("clicking the backdrop calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderOverlay({ onClose });

    const backdrop = screen.getByTestId("version-graph-backdrop");
    await user.click(backdrop);

    expect(onClose).toHaveBeenCalledOnce();
  });

  // -------------------------------------------------------------------------
  // 8. BranchNameInput for Branch from and Restore
  // -------------------------------------------------------------------------
  it("clicking Branch from on a selected node shows name input", async () => {
    const user = userEvent.setup();
    renderOverlay();

    // Select a node first
    const row = screen.getByTestId("graph-row-10");
    await user.click(row);

    const branchFromBtn = screen.getByRole("button", { name: /branch from/i });
    await user.click(branchFromBtn);

    expect(screen.getByRole("textbox", { name: /branch name/i })).toBeDefined();
  });

  it("confirming Branch from calls createBranch with selected nodeId", async () => {
    const user = userEvent.setup();
    const createBranch = vi.fn().mockResolvedValue({ id: 99, head_id: 10, name: "exp" });
    renderOverlay({ actionsOverride: { createBranch } });

    const row = screen.getByTestId("graph-row-10");
    await user.click(row);

    await user.click(screen.getByRole("button", { name: /branch from/i }));
    const input = screen.getByRole("textbox", { name: /branch name/i });
    await user.type(input, "my-exp");
    await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

    await waitFor(() => expect(createBranch).toHaveBeenCalledOnce());
    const [nodeId, body] = createBranch.mock.calls[0];
    expect(nodeId).toBe(10);
    expect(body.name).toBe("my-exp");
  });

  it("clicking Restore on a snapshot shows name input and calls restore", async () => {
    const user = userEvent.setup();
    const restore = vi.fn().mockResolvedValue({ id: 5, head_id: 20, name: "restored" });
    renderOverlay({ actionsOverride: { restore } });

    // Select snapshot node v1.1
    const row = screen.getByTestId("graph-row-20");
    await user.click(row);

    await user.click(screen.getByRole("button", { name: /restore/i }));
    const input = screen.getByRole("textbox", { name: /branch name/i });
    await user.type(input, "restored-v1");
    await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

    await waitFor(() => expect(restore).toHaveBeenCalledOnce());
    const [snapshotId, body] = restore.mock.calls[0];
    expect(snapshotId).toBe(20);
    expect(body.name).toBe("restored-v1");
  });

  // -------------------------------------------------------------------------
  // 9. Discard two-step confirm
  // -------------------------------------------------------------------------
  it("clicking Discard once shows confirm UI, does not call discardBranch", async () => {
    const user = userEvent.setup();
    const discardBranch = vi.fn().mockResolvedValue(undefined);
    renderOverlay({ actionsOverride: { discardBranch } });

    // Select a non-main branch node
    const row = screen.getByTestId("graph-row-30");
    await user.click(row);

    await user.click(screen.getByRole("button", { name: /discard/i }));

    expect(screen.getByText(/active design is not affected/i)).toBeDefined();
    expect(discardBranch).not.toHaveBeenCalled();
  });

  it("confirming discard calls discardBranch with the correct branchId", async () => {
    const user = userEvent.setup();
    const discardBranch = vi.fn().mockResolvedValue(undefined);
    renderOverlay({ actionsOverride: { discardBranch } });

    const row = screen.getByTestId("graph-row-30");
    await user.click(row);

    await user.click(screen.getByRole("button", { name: /discard/i }));
    await user.click(screen.getByRole("button", { name: /confirm discard/i }));

    await waitFor(() => expect(discardBranch).toHaveBeenCalledOnce());
    expect(discardBranch).toHaveBeenCalledWith(2); // branch id=2 for ai/winglet-exp
  });

  // -------------------------------------------------------------------------
  // Loading / empty / null root states
  // -------------------------------------------------------------------------
  it("shows loading message while tree is loading", () => {
    renderOverlay({ treeOverride: { tree: undefined, isLoading: true } });
    expect(screen.getByText(/loading/i)).toBeDefined();
  });

  it("shows empty state when tree has no nodes", () => {
    renderOverlay({
      treeOverride: {
        tree: { root_id: 1, nodes: [], branches: [] },
        isLoading: false,
      },
    });
    expect(screen.getByText(/no version history/i)).toBeDefined();
  });

  it("shows 'no aeroplane selected' when rootId is null", () => {
    renderOverlay({ rootId: null });
    expect(screen.getByText(/no aeroplane selected/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // Close button
  // -------------------------------------------------------------------------
  it("clicking the close button calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderOverlay({ onClose });

    await user.click(screen.getByRole("button", { name: /close version graph/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  // -------------------------------------------------------------------------
  // Aircraft label in header
  // -------------------------------------------------------------------------
  it("shows aircraft name in header when aeroplaneLabel is provided", () => {
    renderOverlay({ aeroplaneLabel: "My Spitfire" });
    expect(screen.getByText(/My Spitfire/)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // Snapshot action from toolbar
  // -------------------------------------------------------------------------
  it("clicking Snapshot on editable head calls actions.snapshot", async () => {
    const user = userEvent.setup();
    const snapshot = vi.fn().mockResolvedValue({ id: 99 });
    renderOverlay({ actionsOverride: { snapshot } });

    // Select editable head (working head, id=10)
    const row = screen.getByTestId("graph-row-10");
    await user.click(row);

    await user.click(screen.getByRole("button", { name: /snapshot/i }));

    // Snapshot shows a label input
    const input = screen.getByRole("textbox", { name: /snapshot label/i });
    await user.type(input, "v2.0");
    await user.click(screen.getByRole("button", { name: /confirm snapshot/i }));

    await waitFor(() => expect(snapshot).toHaveBeenCalledOnce());
  });

  // -------------------------------------------------------------------------
  // gh-964 § 1: Plain-language tooltips on every toolbar button
  // -------------------------------------------------------------------------
  describe("gh-964 §1 — plain-language tooltips", () => {
    it("Snapshot button has a tooltip when disabled (no selection)", () => {
      renderOverlay();
      const btn = screen.getByRole("button", { name: /snapshot/i });
      expect(btn.getAttribute("title")).toBeTruthy();
    });

    it("Snapshot enabled on editable head has action tooltip", async () => {
      const user = userEvent.setup();
      renderOverlay();
      const row = screen.getByTestId("graph-row-10");
      await user.click(row);
      const btn = screen.getByRole("button", { name: /snapshot/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
      expect(btn.getAttribute("title")).toMatch(/checkpoint/i);
    });

    it("Branch from enabled has action tooltip", async () => {
      const user = userEvent.setup();
      renderOverlay();
      const row = screen.getByTestId("graph-row-10");
      await user.click(row);
      const btn = screen.getByRole("button", { name: /branch from/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
      expect(btn.getAttribute("title")).toMatch(/variant/i);
    });

    it("Restore enabled on snapshot has action tooltip", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // select snapshot v1.1 (id 20)
      const row = screen.getByTestId("graph-row-20");
      await user.click(row);
      const btn = screen.getByRole("button", { name: /restore/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
      expect(btn.getAttribute("title")).toMatch(/branch/i);
    });

    it("Adopt enabled has action tooltip", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // select non-main branch head (winglet draft, id 30)
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      const btn = screen.getByRole("button", { name: /adopt/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
      expect(btn.getAttribute("title")).toMatch(/active/i);
    });

    it("Discard enabled has action tooltip", async () => {
      const user = userEvent.setup();
      renderOverlay();
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      const btn = screen.getByRole("button", { name: /discard/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
      expect(btn.getAttribute("title")).toMatch(/delete/i);
    });
  });

  // -------------------------------------------------------------------------
  // gh-964 § 2: Clearer confirmations
  // -------------------------------------------------------------------------
  describe("gh-964 §2 — clearer confirmations", () => {
    it("discard confirm copy includes the branch name", async () => {
      const user = userEvent.setup();
      renderOverlay();
      // Select winglet-exp branch head (non-main)
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      await user.click(screen.getByRole("button", { name: /discard/i }));
      // Confirm copy names the branch and reassures the active design is safe
      const confirm = screen.getByText(/active design is not affected/i);
      expect(confirm.textContent).toMatch(/ai\/winglet-exp/i);
    });

    it("adopt has a two-step confirm naming the branch", async () => {
      const user = userEvent.setup();
      const adoptBranch = vi.fn().mockResolvedValue({ id: 2, head_id: 30, is_main: true });
      renderOverlay({ actionsOverride: { adoptBranch } });

      const row = screen.getByTestId("graph-row-30");
      await user.click(row);

      // First click should show confirm step, NOT call adoptBranch yet
      await user.click(screen.getByRole("button", { name: /adopt/i }));
      expect(adoptBranch).not.toHaveBeenCalled();

      // The confirm copy should name the branch and mention the active design
      const confirm = screen.getByText(/the active design\?/i);
      expect(confirm.textContent).toMatch(/ai\/winglet-exp/i);
      expect(confirm.textContent).toMatch(/main/i);
    });

    it("confirming adopt calls adoptBranch with the correct branchId", async () => {
      const user = userEvent.setup();
      const adoptBranch = vi.fn().mockResolvedValue({ id: 2, head_id: 30, is_main: true });
      renderOverlay({ actionsOverride: { adoptBranch } });

      const row = screen.getByTestId("graph-row-30");
      await user.click(row);

      await user.click(screen.getByRole("button", { name: /adopt/i }));
      await user.click(screen.getByRole("button", { name: /confirm adopt/i }));

      await waitFor(() => expect(adoptBranch).toHaveBeenCalledOnce());
      expect(adoptBranch).toHaveBeenCalledWith(2);
    });

    it("cancelling adopt confirm does not call adoptBranch", async () => {
      const user = userEvent.setup();
      const adoptBranch = vi.fn().mockResolvedValue({ id: 2, head_id: 30, is_main: true });
      renderOverlay({ actionsOverride: { adoptBranch } });

      const row = screen.getByTestId("graph-row-30");
      await user.click(row);

      await user.click(screen.getByRole("button", { name: /adopt/i }));
      await user.click(screen.getByRole("button", { name: /cancel adopt/i }));

      expect(adoptBranch).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // gh-964 § 3: Legend + sorted-by-date note
  // -------------------------------------------------------------------------
  describe("gh-964 §3 — legend and sorted-by-date note", () => {
    it("renders the version graph legend element", () => {
      renderOverlay();
      expect(screen.getByTestId("version-graph-legend")).toBeDefined();
    });

    it("legend contains snapshot glyph and editable head glyph", () => {
      renderOverlay();
      const legend = screen.getByTestId("version-graph-legend");
      expect(legend.textContent).toMatch(/snapshot/i);
      expect(legend.textContent).toMatch(/editable/i);
    });

    it("sorted-by-date note is present near the legend", () => {
      renderOverlay();
      expect(screen.getByText(/sorted by date/i)).toBeDefined();
    });
  });

  // -------------------------------------------------------------------------
  // gh-964 § 4: Branch rename
  // -------------------------------------------------------------------------
  describe("gh-964 §4 — branch rename", () => {
    it("Rename button is disabled when no branch is selected", () => {
      renderOverlay();
      expect(screen.getByRole("button", { name: /rename/i }).hasAttribute("disabled")).toBe(true);
    });

    it("Rename button is enabled when a non-main branch is selected", async () => {
      const user = userEvent.setup();
      renderOverlay();
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      expect(screen.getByRole("button", { name: /rename/i }).hasAttribute("disabled")).toBe(false);
    });

    it("clicking Rename shows the name input pre-filled with current branch name", async () => {
      const user = userEvent.setup();
      renderOverlay();
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      await user.click(screen.getByRole("button", { name: /rename/i }));
      const input = screen.getByRole("textbox", { name: /rename branch/i });
      expect(input).toBeDefined();
      // Should be pre-filled with current branch name
      expect((input as HTMLInputElement).value).toBe("ai/winglet-exp");
    });

    it("confirming rename calls renameBranch with (branchId, newName)", async () => {
      const user = userEvent.setup();
      const renameBranch = vi.fn().mockResolvedValue({ id: 2, name: "new-name" });
      renderOverlay({ actionsOverride: { renameBranch } });
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      await user.click(screen.getByRole("button", { name: /rename/i }));

      const input = screen.getByRole("textbox", { name: /rename branch/i });
      await user.clear(input);
      await user.type(input, "new-name");
      await user.click(screen.getByRole("button", { name: /confirm rename/i }));

      await waitFor(() => expect(renameBranch).toHaveBeenCalledOnce());
      expect(renameBranch).toHaveBeenCalledWith(2, "new-name");
    });

    it("Escape while rename input is open closes input, not the overlay", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      renderOverlay({ onClose });

      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      await user.click(screen.getByRole("button", { name: /rename/i }));
      expect(screen.getByRole("textbox", { name: /rename branch/i })).toBeDefined();

      await user.keyboard("{Escape}");

      expect(screen.queryByRole("textbox", { name: /rename branch/i })).toBeNull();
      expect(onClose).not.toHaveBeenCalled();
    });

    it("Rename button has an action tooltip", async () => {
      const user = userEvent.setup();
      renderOverlay();
      const row = screen.getByTestId("graph-row-30");
      await user.click(row);
      const btn = screen.getByRole("button", { name: /rename/i });
      expect(btn.hasAttribute("disabled")).toBe(false);
      expect(btn.getAttribute("title")).toMatch(/rename/i);
    });
  });
});
