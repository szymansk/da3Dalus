/**
 * Unit tests for the CopilotStrip copilot-proposal affordance (gh-939).
 *
 * Coverage:
 * 1. Proposal detection: branch with created_by="copilot" & !is_main → pending
 * 2. No copilot branch → banner hidden
 * 3. Copilot branch that IS main → banner hidden (already adopted)
 * 4. Banner renders Review / Adopt / Discard buttons when pending
 * 5. Review button visible when onOpenHistory prop is provided; hidden when absent
 * 6. Adopt button calls adoptBranch mutation + revalidates
 * 7. Discard button calls discardBranch mutation + revalidates
 * 8. Banner hidden when aeroplaneId is null
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — must be hoisted before component imports
// ---------------------------------------------------------------------------

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: vi.fn(),
}));

vi.mock("@/hooks/useCopilot", () => ({
  useCopilot: vi.fn(),
  toolLabel: (name: string) => `tool:${name}`,
}));

const mockUseAeroplanes = vi.fn();
vi.mock("@/hooks/useAeroplanes", () => ({
  useAeroplanes: () => mockUseAeroplanes(),
}));

const mockUseLineageTree = vi.fn();
const mockUseVersionActions = vi.fn();
vi.mock("@/hooks/useVersioning", () => ({
  useLineageTree: (...args: unknown[]) => mockUseLineageTree(...args),
  useVersionActions: (...args: unknown[]) => mockUseVersionActions(...args),
  useCompareNodes: vi.fn(() => ({ compareOut: undefined, isLoading: false, error: undefined })),
}));

// Streamdown — used inside CopilotStrip's AssistantBubble; stub to avoid markdown deps in JSDOM.
vi.mock("streamdown", () => ({
  Streamdown: ({ children }: { children: React.ReactNode }) =>
    React.createElement("span", {}, children),
  defaultRemarkPlugins: { gfm: "gfm", codeMeta: "codeMeta" },
}));

vi.mock("remark-math", () => ({ default: {} }));
vi.mock("remark-breaks", () => ({ default: {} }));
vi.mock("rehype-katex", () => ({ default: {} }));

// ---------------------------------------------------------------------------
// Lazy imports (after mocks)
// ---------------------------------------------------------------------------

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useCopilot } from "@/hooks/useCopilot";
import type { UseCopilotReturn } from "@/hooks/useCopilot";
import { CopilotStrip } from "@/components/workbench/CopilotStrip";
import type { TreeOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const AEROPLANE_CTX_WITH_ID = {
  aeroplaneId: "aero-uuid-1" as string | null,
  hydrated: true,
  selectedWing: null,
  selectedXsecIndex: null,
  selectedFuselage: null,
  selectedFuselageXsecIndex: null,
  treeMode: "wingconfig" as const,
  pickerOpen: false,
  lastImportWarnings: null,
  setAeroplaneId: vi.fn(),
  selectWing: vi.fn(),
  selectXsec: vi.fn(),
  selectFuselage: vi.fn(),
  selectFuselageXsec: vi.fn(),
  setTreeMode: vi.fn(),
  openPicker: vi.fn(),
  closePicker: vi.fn(),
  setLastImportWarnings: vi.fn(),
};

const COPILOT_DEFAULT: UseCopilotReturn = {
  history: undefined,
  historyLoading: false,
  historyError: null,
  streamingText: "",
  activeToolLabel: null,
  errorMessage: null,
  isSending: false,
  sendMessage: vi.fn().mockResolvedValue(undefined),
  clearError: vi.fn(),
};

/** Aeroplane with versioning metadata. */
const FAKE_AEROPLANE = {
  id: "aero-uuid-1",
  name: "Test Plane",
  total_mass_kg: null,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
  int_id: 10,
  root_id: 10,
  branch_name: "main",
  is_main_branch: true,
};

/** Tree with a copilot branch (pending proposal). */
const TREE_WITH_COPILOT_BRANCH: TreeOut = {
  root_id: 10,
  nodes: [
    {
      id: 10,
      uuid: "aaa",
      name: "Test Plane",
      branch_id: 1,
      predecessor_id: null,
      root_id: 10,
      is_immutable: false,
      is_head: true,
      version_label: null,
      version_note: null,
      created_by: "human",
      created_at: "2026-06-01T00:00:00Z",
    },
    {
      id: 20,
      uuid: "bbb",
      name: "Test Plane",
      branch_id: 2,
      predecessor_id: 10,
      root_id: 10,
      is_immutable: false,
      is_head: true,
      version_label: null,
      version_note: null,
      created_by: "copilot",
      created_at: "2026-06-02T00:00:00Z",
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
      created_at: "2026-06-01T00:00:00Z",
    },
    {
      id: 2,
      root_id: 10,
      head_id: 20,
      name: "copilot/wing-tweak",
      is_main: false,
      created_by: "copilot",
      created_at: "2026-06-02T00:00:00Z",
    },
  ],
};

/** Tree where the copilot branch IS already main (should NOT show banner). */
const TREE_COPILOT_BRANCH_IS_MAIN: TreeOut = {
  root_id: 10,
  nodes: [],
  branches: [
    {
      id: 1,
      root_id: 10,
      head_id: 10,
      name: "copilot/already-main",
      is_main: true,    // <-- already main, not pending
      created_by: "copilot",
      created_at: "2026-06-01T00:00:00Z",
    },
  ],
};

/** Tree with no copilot branch at all. */
const TREE_NO_COPILOT_BRANCH: TreeOut = {
  root_id: 10,
  nodes: [],
  branches: [
    {
      id: 1,
      root_id: 10,
      head_id: 10,
      name: "main",
      is_main: true,
      created_by: "human",
      created_at: "2026-06-01T00:00:00Z",
    },
  ],
};

// ---------------------------------------------------------------------------
// Setup helpers
// ---------------------------------------------------------------------------

const mockAdoptBranch = vi.fn();
const mockDiscardBranch = vi.fn();

function setupMocksWithTree(tree: TreeOut | undefined, aeroplaneId: string | null = "aero-uuid-1") {
  vi.mocked(useAeroplaneContext).mockReturnValue({
    ...AEROPLANE_CTX_WITH_ID,
    aeroplaneId,
  });
  vi.mocked(useCopilot).mockReturnValue(COPILOT_DEFAULT);
  mockUseAeroplanes.mockReturnValue({
    aeroplanes: aeroplaneId ? [FAKE_AEROPLANE] : [],
    createAeroplane: vi.fn(),
    deleteAeroplane: vi.fn(),
  });
  mockUseLineageTree.mockReturnValue({
    tree,
    isLoading: false,
    error: undefined,
    mutate: vi.fn(),
  });
  mockUseVersionActions.mockReturnValue({
    snapshot: vi.fn(),
    createBranch: vi.fn(),
    adoptBranch: mockAdoptBranch,
    restore: vi.fn(),
    discardBranch: mockDiscardBranch,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockAdoptBranch.mockResolvedValue({ id: 2, root_id: 10, head_id: 10, name: "copilot/wing-tweak", is_main: true, created_by: "copilot", created_at: "2026-06-02T00:00:00Z" });
  mockDiscardBranch.mockResolvedValue(undefined);
});

// ---------------------------------------------------------------------------
// 1. Proposal detection: copilot branch (not main) → banner shown
// ---------------------------------------------------------------------------

describe("CopilotStrip — proposal detection", () => {
  it("shows the proposal banner when a non-main copilot branch exists in the tree", () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    render(<CopilotStrip />);
    expect(screen.getByTestId("copilot-proposal-banner")).toBeInTheDocument();
    expect(screen.getByText("Copilot proposal pending")).toBeInTheDocument();
  });

  it("hides the banner when there is no copilot branch", () => {
    setupMocksWithTree(TREE_NO_COPILOT_BRANCH);
    render(<CopilotStrip />);
    expect(screen.queryByTestId("copilot-proposal-banner")).toBeNull();
  });

  it("hides the banner when the copilot branch is already is_main=true", () => {
    setupMocksWithTree(TREE_COPILOT_BRANCH_IS_MAIN);
    render(<CopilotStrip />);
    expect(screen.queryByTestId("copilot-proposal-banner")).toBeNull();
  });

  it("hides the banner when no aeroplane is selected", () => {
    setupMocksWithTree(undefined, null);
    vi.mocked(useAeroplaneContext).mockReturnValue({
      ...AEROPLANE_CTX_WITH_ID,
      aeroplaneId: null,
    });
    render(<CopilotStrip />);
    expect(screen.queryByTestId("copilot-proposal-banner")).toBeNull();
  });

  it("hides the banner when the lineage tree is not yet loaded (undefined)", () => {
    setupMocksWithTree(undefined);
    render(<CopilotStrip />);
    expect(screen.queryByTestId("copilot-proposal-banner")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 2. Banner renders Review / Adopt / Discard
// ---------------------------------------------------------------------------

describe("CopilotStrip — proposal banner buttons", () => {
  it("renders Adopt and Discard buttons", () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    render(<CopilotStrip />);
    expect(screen.getByRole("button", { name: "Adopt copilot proposal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discard copilot proposal" })).toBeInTheDocument();
  });

  it("shows Review button when onOpenHistory prop is provided", () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    render(<CopilotStrip onOpenHistory={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Review copilot proposal" })).toBeInTheDocument();
  });

  it("hides Review button when onOpenHistory prop is not provided", () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    render(<CopilotStrip />);
    expect(screen.queryByRole("button", { name: "Review copilot proposal" })).toBeNull();
  });

  it("calls onOpenHistory when Review is clicked", async () => {
    const onOpenHistory = vi.fn();
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    const user = userEvent.setup();
    render(<CopilotStrip onOpenHistory={onOpenHistory} />);
    await user.click(screen.getByRole("button", { name: "Review copilot proposal" }));
    expect(onOpenHistory).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// 3. Adopt mutation
// ---------------------------------------------------------------------------

describe("CopilotStrip — Adopt action", () => {
  it("calls adoptBranch with the proposal branch id when Adopt is clicked", async () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Adopt copilot proposal" }));
    await waitFor(() => expect(mockAdoptBranch).toHaveBeenCalledWith(2));
  });

  it("revalidates after adopt (useVersionActions handles revalidation automatically)", async () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Adopt copilot proposal" }));
    await waitFor(() => expect(mockAdoptBranch).toHaveBeenCalledOnce());
    // useVersionActions internally calls globalMutate for the tree and aeroplanes list.
    // This is verified in useVersioning.test.tsx; here we only verify the mutation is called.
  });
});

// ---------------------------------------------------------------------------
// 4. Discard mutation
// ---------------------------------------------------------------------------

describe("CopilotStrip — Discard action", () => {
  it("calls discardBranch with the proposal branch id when Discard is clicked", async () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Discard copilot proposal" }));
    await waitFor(() => expect(mockDiscardBranch).toHaveBeenCalledWith(2));
  });

  it("revalidates after discard", async () => {
    setupMocksWithTree(TREE_WITH_COPILOT_BRANCH);
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Discard copilot proposal" }));
    await waitFor(() => expect(mockDiscardBranch).toHaveBeenCalledOnce());
  });
});
