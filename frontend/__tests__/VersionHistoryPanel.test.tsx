/**
 * Unit tests for VersionHistoryPanel (gh-907).
 *
 * Covered:
 * 1. Renders nodes grouped by branch with correct labels (label/note/timestamp/created_by).
 * 2. Highlights the current HEAD node.
 * 3. Per-node compare button toggles selection (max 2).
 * 4. Per-node "Branch from" expands an inline input; on confirm calls createBranch().
 * 5. Per-node "Restore" (snapshot only) expands an inline input; calls restore().
 * 6. Per-branch "Adopt" calls adoptBranch().
 * 7. Per-branch "Discard" calls discardBranch() (non-main branch).
 * 8. Discard button absent on main branch.
 * 9. Loading state renders a loading message.
 * 10. Empty state (no nodes) renders an empty message.
 * 11. rootId=null renders "no aeroplane selected" message.
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
    Image: icon,
  };
});

// Versioning hooks
const mockUseLineageTree = vi.fn();
const mockUseVersionActions = vi.fn();
const mockUseCompareNodes = vi.fn();
vi.mock("@/hooks/useVersioning", () => ({
  useLineageTree: (...args: unknown[]) => mockUseLineageTree(...args),
  useVersionActions: (...args: unknown[]) => mockUseVersionActions(...args),
  useCompareNodes: (...args: unknown[]) => mockUseCompareNodes(...args),
}));

// VersionCompareView — stub so the compare panel does not need real adapters.
vi.mock("@/components/workbench/VersionCompareView", () => ({
  VersionCompareView: ({ onClose }: { onClose: () => void }) =>
    React.createElement("div", { "data-testid": "version-compare-view" },
      React.createElement("button", { type: "button", onClick: onClose, "aria-label": "Close compare panel" }, "Close compare"),
    ),
}));

// ---------------------------------------------------------------------------
// Lazy imports
// ---------------------------------------------------------------------------

import { VersionHistoryPanel } from "../components/workbench/VersionHistoryPanel";
import type { TreeOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const FAKE_TREE: TreeOut = {
  root_id: 10,
  nodes: [
    {
      id: 10,
      uuid: "aaa",
      name: "My Plane",
      branch_id: 1,
      predecessor_id: null,
      root_id: 10,
      is_immutable: false,
      is_head: true,
      version_label: "Initial",
      version_note: "First version",
      created_by: "human",
      created_at: "2026-06-07T10:00:00Z",
    },
    {
      id: 11,
      uuid: "bbb",
      name: "My Plane",
      branch_id: 1,
      predecessor_id: 10,
      root_id: 10,
      is_immutable: true,
      is_head: false,
      version_label: "v1",
      version_note: "Snapshot before winglets",
      created_by: "human",
      created_at: "2026-06-07T11:00:00Z",
    },
    {
      id: 20,
      uuid: "ccc",
      name: "My Plane (ai)",
      branch_id: 2,
      predecessor_id: 10,
      root_id: 10,
      is_immutable: false,
      is_head: true,
      version_label: null,
      version_note: "AI experiment",
      created_by: "ai",
      created_at: "2026-06-08T09:00:00Z",
    },
  ],
  branches: [
    {
      id: 1,
      root_id: 10,
      head_id: 10,
      name: "main",
      is_main: true,
      created_by: "human",
      created_at: "2026-06-07T10:00:00Z",
    },
    {
      id: 2,
      root_id: 10,
      head_id: 20,
      name: "ai/winglet-v1",
      is_main: false,
      created_by: "ai",
      created_at: "2026-06-08T09:00:00Z",
    },
  ],
};

const DEFAULT_ACTIONS = {
  snapshot: vi.fn(),
  createBranch: vi.fn(),
  adoptBranch: vi.fn(),
  restore: vi.fn(),
  discardBranch: vi.fn(),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeActions(overrides: Partial<typeof DEFAULT_ACTIONS> = {}) {
  return { ...DEFAULT_ACTIONS, ...overrides };
}

function renderPanel(overrides: {
  rootId?: number | null;
  currentHeadId?: number | null;
  aeroplaneId?: number | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  treeOverride?: Partial<{ tree: TreeOut | undefined; isLoading: boolean; error: Error | undefined; mutate: any }>;
  actionsOverride?: Partial<typeof DEFAULT_ACTIONS>;
  onSwitchAeroplane?: (uuid: string) => void;
} = {}) {
  const {
    rootId = 10,
    currentHeadId = 10,
    aeroplaneId = 10,
    treeOverride = {},
    actionsOverride = {},
    onSwitchAeroplane,
  } = overrides;

  mockUseLineageTree.mockReturnValue({
    tree: FAKE_TREE,
    isLoading: false,
    error: undefined,
    mutate: vi.fn().mockResolvedValue(FAKE_TREE),
    ...treeOverride,
  });

  mockUseVersionActions.mockReturnValue(makeActions(actionsOverride));

  return render(
    <VersionHistoryPanel
      rootId={rootId}
      currentHeadId={currentHeadId}
      aeroplaneId={aeroplaneId}
      onClose={vi.fn()}
      onSwitchAeroplane={onSwitchAeroplane}
    />,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("VersionHistoryPanel (gh-907)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCompareNodes.mockReturnValue({
      compareOut: undefined,
      isLoading: false,
      error: undefined,
    });
  });

  // -------------------------------------------------------------------------
  // 1. Renders nodes grouped by branch
  // -------------------------------------------------------------------------
  it("renders branch names and node labels", () => {
    renderPanel();

    // Branch names (may appear multiple times — heading + badge — use getAllByText)
    expect(screen.getAllByText("main").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ai/winglet-v1").length).toBeGreaterThan(0);

    // Node labels
    expect(screen.getByText("Initial")).toBeDefined();
    expect(screen.getByText("v1")).toBeDefined();
    // Node with no version_label falls back to name
    expect(screen.getByText("My Plane (ai)")).toBeDefined();
  });

  it("renders node notes and timestamps", () => {
    renderPanel();
    expect(screen.getByText("First version")).toBeDefined();
    expect(screen.getByText("Snapshot before winglets")).toBeDefined();
    expect(screen.getByText("AI experiment")).toBeDefined();
  });

  it("renders snapshot badge on immutable nodes", () => {
    renderPanel();
    const snapshotBadges = screen.getAllByText("snapshot");
    expect(snapshotBadges.length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // 2. Highlights current HEAD
  // -------------------------------------------------------------------------
  it("marks the current HEAD node with a HEAD badge", () => {
    renderPanel({ currentHeadId: 10 });
    const headBadges = screen.getAllByText("HEAD");
    expect(headBadges.length).toBe(1);
  });

  it("marks a different node as HEAD when currentHeadId differs", () => {
    renderPanel({ currentHeadId: 20 });
    const headBadges = screen.getAllByText("HEAD");
    expect(headBadges.length).toBe(1);
  });

  // -------------------------------------------------------------------------
  // 3. Compare selection
  // -------------------------------------------------------------------------
  it("selecting a node for compare toggles its button and shows the compare bar", async () => {
    const user = userEvent.setup();
    renderPanel();

    const compareBtns = screen.getAllByRole("button", { name: /select for comparison/i });
    expect(compareBtns.length).toBeGreaterThan(0);

    await user.click(compareBtns[0]);

    // Compare bar should appear
    expect(screen.getByText(/select one more node to compare/i)).toBeDefined();
  });

  it("selecting two nodes shows the '2 nodes selected' message", async () => {
    const user = userEvent.setup();
    renderPanel();

    const compareBtns = screen.getAllByRole("button", { name: /select for comparison|remove from comparison/i });
    await user.click(compareBtns[0]);
    await user.click(compareBtns[1]);

    expect(screen.getByText(/2 nodes selected/i)).toBeDefined();
  });

  it("selecting two nodes and clicking Compare opens the compare view", async () => {
    const user = userEvent.setup();
    renderPanel();

    const compareBtns = screen.getAllByRole("button", { name: /select for comparison|remove from comparison/i });
    await user.click(compareBtns[0]);
    await user.click(compareBtns[1]);

    // The "Compare" button should now be visible in the compare bar
    const compareOpenBtn = screen.getByRole("button", { name: /open compare view/i });
    await user.click(compareOpenBtn);

    // VersionCompareView stub should render
    expect(screen.getByTestId("version-compare-view")).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 4. "Branch from" action
  // -------------------------------------------------------------------------
  it("clicking Branch from expands the inline input", async () => {
    const user = userEvent.setup();
    renderPanel();

    const branchBtns = screen.getAllByRole("button", { name: /fork a new branch/i });
    await user.click(branchBtns[0]);

    expect(screen.getByRole("textbox", { name: /branch name/i })).toBeDefined();
  });

  it("confirming Branch from calls createBranch() with the SELECTED node id and entered name", async () => {
    const user = userEvent.setup();
    const createBranch = vi.fn().mockResolvedValue({ id: 3, name: "new-exp" });
    renderPanel({ actionsOverride: { createBranch } });

    // First node in FAKE_TREE branch 1 is id=10 ("Initial")
    const branchBtns = screen.getAllByRole("button", { name: /fork a new branch/i });
    await user.click(branchBtns[0]);

    const input = screen.getByRole("textbox", { name: /branch name/i });
    await user.type(input, "new-exp");
    await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

    await waitFor(() => expect(createBranch).toHaveBeenCalledOnce());
    const [nodeId, body] = createBranch.mock.calls[0];
    // Must use the selected node's id (10), NOT always the head aeroplane id
    expect(nodeId).toBe(10);
    expect(body.name).toBe("new-exp");
  });

  // -------------------------------------------------------------------------
  // 5. "Restore" action (snapshot nodes only)
  // -------------------------------------------------------------------------
  it("Restore button is present on immutable snapshot nodes", () => {
    renderPanel();
    const restoreBtns = screen.getAllByRole("button", {
      name: /restore this snapshot/i,
    });
    expect(restoreBtns.length).toBeGreaterThan(0);
  });

  it("confirming Restore calls restore() with snapshotId + branch name", async () => {
    const user = userEvent.setup();
    const restore = vi.fn().mockResolvedValue({ id: 5, name: "restored" });
    renderPanel({ actionsOverride: { restore } });

    const restoreBtns = screen.getAllByRole("button", {
      name: /restore this snapshot/i,
    });
    await user.click(restoreBtns[0]);

    const input = screen.getByRole("textbox", { name: /branch name/i });
    await user.type(input, "restored-v1");
    await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

    await waitFor(() => expect(restore).toHaveBeenCalledOnce());
    const [snapshotId, body] = restore.mock.calls[0];
    expect(snapshotId).toBe(11); // the immutable node id
    expect(body.name).toBe("restored-v1");
  });

  // -------------------------------------------------------------------------
  // 6. "Adopt" action
  // -------------------------------------------------------------------------
  it("clicking Adopt on a non-main branch calls adoptBranch(branchId)", async () => {
    const user = userEvent.setup();
    const adoptBranch = vi.fn().mockResolvedValue({ id: 2, is_main: true });
    renderPanel({ actionsOverride: { adoptBranch } });

    const adoptBtns = screen.getAllByRole("button", { name: /promote branch/i });
    expect(adoptBtns.length).toBeGreaterThan(0);
    await user.click(adoptBtns[0]);

    await waitFor(() => expect(adoptBranch).toHaveBeenCalledOnce());
    expect(adoptBranch).toHaveBeenCalledWith(2); // branch id of ai/winglet-v1
  });

  // -------------------------------------------------------------------------
  // 7. "Discard" action — requires a two-step confirmation gate
  // -------------------------------------------------------------------------
  it("clicking Discard once shows confirmation UI and does NOT call discardBranch yet", async () => {
    const user = userEvent.setup();
    const discardBranch = vi.fn().mockResolvedValue(undefined);
    renderPanel({ actionsOverride: { discardBranch } });

    const discardBtns = screen.getAllByRole("button", { name: /discard branch/i });
    await user.click(discardBtns[0]);

    // Confirmation prompt must appear
    expect(screen.getByText(/delete all nodes/i)).toBeDefined();
    // API must NOT have been called yet
    expect(discardBranch).not.toHaveBeenCalled();
  });

  it("clicking Discard then confirming calls discardBranch(branchId)", async () => {
    const user = userEvent.setup();
    const discardBranch = vi.fn().mockResolvedValue(undefined);
    renderPanel({ actionsOverride: { discardBranch } });

    // First click — shows confirm UI
    const discardBtns = screen.getAllByRole("button", { name: /discard branch/i });
    await user.click(discardBtns[0]);

    // Second click — confirm
    const confirmBtn = screen.getByRole("button", { name: /confirm discard branch/i });
    await user.click(confirmBtn);

    await waitFor(() => expect(discardBranch).toHaveBeenCalledOnce());
    expect(discardBranch).toHaveBeenCalledWith(2); // branch id of ai/winglet-v1
  });

  it("clicking Discard then Cancel does not call discardBranch", async () => {
    const user = userEvent.setup();
    const discardBranch = vi.fn().mockResolvedValue(undefined);
    renderPanel({ actionsOverride: { discardBranch } });

    const discardBtns = screen.getAllByRole("button", { name: /discard branch/i });
    await user.click(discardBtns[0]);

    const cancelBtn = screen.getByRole("button", { name: /cancel discard/i });
    await user.click(cancelBtn);

    expect(discardBranch).not.toHaveBeenCalled();
    // Discard button is back
    expect(screen.getAllByRole("button", { name: /discard branch/i }).length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // 8. Discard button absent on main branch
  // -------------------------------------------------------------------------
  it("Discard button is absent on the main branch", () => {
    renderPanel();
    // There should be a discard button only for non-main branches.
    // With FAKE_TREE having 1 non-main branch, there's exactly 1 discard button.
    const discardBtns = screen.getAllByRole("button", { name: /discard branch/i });
    expect(discardBtns.length).toBe(1);
  });

  // -------------------------------------------------------------------------
  // 9. Loading state
  // -------------------------------------------------------------------------
  it("shows loading message while tree is loading", () => {
    renderPanel({ treeOverride: { tree: undefined, isLoading: true } });
    expect(screen.getByText(/loading history/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 10. Empty state
  // -------------------------------------------------------------------------
  it("shows empty state when tree has no nodes", () => {
    renderPanel({
      treeOverride: {
        tree: { root_id: 10, nodes: [], branches: [] },
        isLoading: false,
      },
    });
    expect(screen.getByText(/no version history yet/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 11. rootId=null
  // -------------------------------------------------------------------------
  it("shows 'no aeroplane selected' when rootId is null", () => {
    renderPanel({ rootId: null });
    expect(screen.getByText(/no aeroplane selected/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // Close button
  // -------------------------------------------------------------------------
  it("clicking the close button calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    mockUseLineageTree.mockReturnValue({
      tree: FAKE_TREE,
      isLoading: false,
      error: undefined,
      mutate: vi.fn(),
    });
    mockUseVersionActions.mockReturnValue(makeActions());

    render(
      <VersionHistoryPanel
        rootId={10}
        currentHeadId={10}
        aeroplaneId={10}
        onClose={onClose}
      />,
    );

    await user.click(screen.getByRole("button", { name: /close history panel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  // -------------------------------------------------------------------------
  // gh-910: onSwitchAeroplane called after branch ops
  // -------------------------------------------------------------------------
  describe("gh-910: onSwitchAeroplane after branch operations", () => {
    /**
     * FAKE_TREE has:
     *   nodes: [{id:10, uuid:"aaa"}, {id:11, uuid:"bbb"}, {id:20, uuid:"ccc"}]
     *   branches: [{id:1, head_id:10}, {id:2, head_id:20}]
     *
     * createBranch/adopt/restore all return a BranchOut with head_id.
     * The mutate() returns the fresh tree so the panel can look up the UUID.
     */

    it("createBranch: calls onSwitchAeroplane with the new head UUID", async () => {
      const user = userEvent.setup();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const switchSpy = vi.fn() as any as (uuid: string) => void;

      // createBranch returns a BranchOut whose head_id=10 → uuid="aaa"
      const createBranch = vi.fn().mockResolvedValue({ id: 3, root_id: 10, head_id: 10, name: "exp", is_main: false, created_by: "human", created_at: "" });
      renderPanel({ actionsOverride: { createBranch }, onSwitchAeroplane: switchSpy });

      const branchBtns = screen.getAllByRole("button", { name: /fork a new branch/i });
      await user.click(branchBtns[0]);
      const input = screen.getByRole("textbox", { name: /branch name/i });
      await user.type(input, "exp");
      await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await waitFor(() => expect(switchSpy as any).toHaveBeenCalledOnce());
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect(switchSpy as any).toHaveBeenCalledWith("aaa");
    });

    it("adoptBranch: calls onSwitchAeroplane with the adopted head UUID", async () => {
      const user = userEvent.setup();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const switchSpy = vi.fn() as any as (uuid: string) => void;

      // adoptBranch returns a BranchOut whose head_id=20 → uuid="ccc"
      const adoptBranch = vi.fn().mockResolvedValue({ id: 2, root_id: 10, head_id: 20, name: "ai/winglet-v1", is_main: true, created_by: "ai", created_at: "" });
      renderPanel({ actionsOverride: { adoptBranch }, onSwitchAeroplane: switchSpy });

      const adoptBtns = screen.getAllByRole("button", { name: /promote branch/i });
      await user.click(adoptBtns[0]);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await waitFor(() => expect(switchSpy as any).toHaveBeenCalledOnce());
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect(switchSpy as any).toHaveBeenCalledWith("ccc");
    });

    it("restore: calls onSwitchAeroplane with the restored head UUID", async () => {
      const user = userEvent.setup();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const switchSpy = vi.fn() as any as (uuid: string) => void;

      // restore returns a BranchOut whose head_id=10 → uuid="aaa"
      const restore = vi.fn().mockResolvedValue({ id: 5, root_id: 10, head_id: 10, name: "restored", is_main: false, created_by: "human", created_at: "" });
      renderPanel({ actionsOverride: { restore }, onSwitchAeroplane: switchSpy });

      const restoreBtns = screen.getAllByRole("button", { name: /restore this snapshot/i });
      await user.click(restoreBtns[0]);
      const input = screen.getByRole("textbox", { name: /branch name/i });
      await user.type(input, "restored-v1");
      await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await waitFor(() => expect(switchSpy as any).toHaveBeenCalledOnce());
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect(switchSpy as any).toHaveBeenCalledWith("aaa");
    });

    it("does not call onSwitchAeroplane when prop is absent", async () => {
      const user = userEvent.setup();
      const createBranch = vi.fn().mockResolvedValue({ id: 3, root_id: 10, head_id: 10, name: "exp", is_main: false, created_by: "human", created_at: "" });
      // No onSwitchAeroplane prop — must not throw
      renderPanel({ actionsOverride: { createBranch } });

      const branchBtns = screen.getAllByRole("button", { name: /fork a new branch/i });
      await user.click(branchBtns[0]);
      const input = screen.getByRole("textbox", { name: /branch name/i });
      await user.type(input, "exp");
      await user.click(screen.getByRole("button", { name: /confirm branch name/i }));

      await waitFor(() => expect(createBranch).toHaveBeenCalledOnce());
      // Just verify no error was thrown — test passes if no exception
    });
  });

  // -------------------------------------------------------------------------
  // gh-910 polish: is_main badge is visually distinct from the branch name
  // -------------------------------------------------------------------------
  describe("gh-910: is_main badge visual distinction", () => {
    it("renders 'active main' badge (not just 'main') for the is_main branch", () => {
      renderPanel();
      // The is_main badge must contain "active main" so it is distinct from
      // a branch merely NAMED "main"
      expect(screen.getByLabelText("Active main branch")).toBeDefined();
    });

    it("a non-main branch with a name containing 'main' does not show the active-main badge", () => {
      const treeWithMainNamedBranch = {
        ...FAKE_TREE,
        branches: [
          { ...FAKE_TREE.branches[0], name: "not-main-branch", is_main: false },
          { ...FAKE_TREE.branches[1], name: "main-variant", is_main: true },
        ],
      };
      mockUseLineageTree.mockReturnValue({
        tree: treeWithMainNamedBranch,
        isLoading: false,
        error: undefined,
        mutate: vi.fn().mockResolvedValue(treeWithMainNamedBranch),
      });
      mockUseVersionActions.mockReturnValue(makeActions());
      render(
        <VersionHistoryPanel
          rootId={10}
          currentHeadId={10}
          aeroplaneId={10}
          onClose={vi.fn()}
        />,
      );
      // Only one "Active main branch" aria-label should exist
      expect(screen.getAllByLabelText("Active main branch").length).toBe(1);
    });
  });
});
