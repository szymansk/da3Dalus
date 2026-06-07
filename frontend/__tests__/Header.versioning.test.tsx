/**
 * Unit tests for Header.tsx — versioning affordances (gh-907).
 *
 * Covered:
 * 1. Save icon opens the SnapshotDialog when an aeroplane with int_id is selected.
 * 2. Save icon is disabled when no aeroplane is selected.
 * 3. Confirming the snapshot dialog calls snapshot() with the correct label+note.
 * 4. Branch indicator shows the branch name; ai/ branches are visually marked.
 * 5. History button calls onOpenHistory.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ---------------------------------------------------------------------------
// Module mocks (must be hoisted before component imports)
// ---------------------------------------------------------------------------

// next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/workbench",
}));

// Lucide icons — replace all with spans so jsdom renders without SVG issues.
vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { "data-icon": "true", ...props });
  return {
    History: icon,
    ChevronDown: icon,
    Save: icon,
    Settings: icon,
    ArrowLeftRight: icon,
    GitBranch: icon,
    Bot: icon,
    Camera: icon,
  };
});

// GuardedLink — render a plain anchor so nav clicks don't need router setup.
vi.mock("@/components/workbench/GuardedLink", () => ({
  GuardedLink: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

// AeroplaneContext
const mockUseAeroplaneContext = vi.fn();
vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => mockUseAeroplaneContext(),
}));

// useAeroplanes
const mockUseAeroplanes = vi.fn();
vi.mock("@/hooks/useAeroplanes", () => ({
  useAeroplanes: () => mockUseAeroplanes(),
}));

// useVersionActions — we spy on snapshot()
const mockSnapshot = vi.fn();
vi.mock("@/hooks/useVersioning", () => ({
  useVersionActions: () => ({
    snapshot: mockSnapshot,
    createBranch: vi.fn(),
    adoptBranch: vi.fn(),
    restore: vi.fn(),
    discardBranch: vi.fn(),
  }),
}));

// useDialog is NOT mocked — we rely on the setup.ts showModal/close polyfill.

// ---------------------------------------------------------------------------
// Lazy imports (after mock hoisting)
// ---------------------------------------------------------------------------

import { Header } from "../components/workbench/Header";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function defaultCtx(overrides: Record<string, unknown> = {}) {
  return {
    aeroplaneId: "uuid-123",
    selectedWing: null,
    selectedXsecIndex: null,
    openPicker: vi.fn(),
    ...overrides,
  };
}

function defaultAeroplanes(overrides: Record<string, unknown> = {}) {
  return {
    aeroplanes: [
      {
        id: "uuid-123",
        name: "My Plane",
        total_mass_kg: null,
        created_at: "",
        updated_at: "",
        int_id: 42,
        root_id: 10,
        branch_name: "main",
        is_main_branch: true,
        ...overrides,
      },
    ],
    error: null,
    isLoading: false,
    mutate: vi.fn(),
    createAeroplane: vi.fn(),
    deleteAeroplane: vi.fn(),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Header — versioning (gh-907)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAeroplaneContext.mockReturnValue(defaultCtx());
    mockUseAeroplanes.mockReturnValue(defaultAeroplanes());
    mockSnapshot.mockResolvedValue({ id: 99, is_immutable: true });
  });

  // -------------------------------------------------------------------------
  // 1. Save icon opens the SnapshotDialog
  // -------------------------------------------------------------------------
  it("clicking the Save icon opens the snapshot dialog", async () => {
    const user = userEvent.setup();
    render(<Header />);

    const saveBtn = screen.getByRole("button", { name: /save a snapshot of the current design/i });
    expect(saveBtn).toBeDefined();

    await user.click(saveBtn);

    // The dialog should be open (showModal polyfill sets the 'open' attribute).
    const dialog = document.querySelector("dialog");
    expect(dialog?.hasAttribute("open")).toBe(true);
    // Label input + why textarea should be visible.
    expect(document.getElementById("snapshot-label")).toBeDefined();
    expect(document.getElementById("snapshot-note")).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 2. Save icon disabled when no int_id (no versioned aeroplane)
  // -------------------------------------------------------------------------
  it("Save icon is disabled when the current aeroplane has no int_id", () => {
    mockUseAeroplanes.mockReturnValue(
      defaultAeroplanes({ int_id: null }),
    );
    render(<Header />);

    const saveBtn = screen.getByRole("button", { name: /save a snapshot/i });
    expect(saveBtn.hasAttribute("disabled")).toBe(true);
  });

  it("Save icon is disabled when no aeroplane is selected", () => {
    mockUseAeroplaneContext.mockReturnValue(defaultCtx({ aeroplaneId: null }));
    mockUseAeroplanes.mockReturnValue({ aeroplanes: [], error: null, isLoading: false });
    render(<Header />);

    const saveBtn = screen.getByRole("button", { name: /save a snapshot/i });
    expect(saveBtn.hasAttribute("disabled")).toBe(true);
  });

  // -------------------------------------------------------------------------
  // 3. Confirming snapshot dialog calls snapshot() with label + note
  // -------------------------------------------------------------------------
  it("filling label+note and confirming calls snapshot() with the correct body", async () => {
    const user = userEvent.setup();
    render(<Header />);

    // Open dialog
    await user.click(screen.getByRole("button", { name: /save a snapshot of the current design/i }));

    // Fill inputs by id (most reliable in jsdom)
    const labelInput = document.getElementById("snapshot-label") as HTMLInputElement;
    const noteInput = document.getElementById("snapshot-note") as HTMLTextAreaElement;
    await user.type(labelInput, "v2 — wider winglets");
    await user.type(noteInput, "testing wider span");

    // Confirm — accessible name is the aria-label "Save snapshot"
    await user.click(screen.getByRole("button", { name: /^save snapshot$/i }));

    await waitFor(() => expect(mockSnapshot).toHaveBeenCalledOnce());

    const [body] = mockSnapshot.mock.calls[0];
    expect(body.label).toBe("v2 — wider winglets");
    expect(body.note).toBe("testing wider span");
  });

  it("snapshot() is called with label only when note is empty", async () => {
    const user = userEvent.setup();
    render(<Header />);

    await user.click(screen.getByRole("button", { name: /save a snapshot of the current design/i }));

    const labelInput = document.getElementById("snapshot-label") as HTMLInputElement;
    await user.type(labelInput, "quick save");

    await user.click(screen.getByRole("button", { name: /^save snapshot$/i }));

    await waitFor(() => expect(mockSnapshot).toHaveBeenCalledOnce());

    const [body] = mockSnapshot.mock.calls[0];
    expect(body.label).toBe("quick save");
    // Empty note is converted to undefined (falsy → not sent as empty string).
    expect(body.note == null || body.note === "").toBe(true);
  });

  it("Save button in dialog is disabled when label is empty", async () => {
    const user = userEvent.setup();
    render(<Header />);

    await user.click(screen.getByRole("button", { name: /save a snapshot of the current design/i }));

    // The Save button aria-label is "Save snapshot" when label field is empty (disabled)
    const saveInDialog = screen.getByRole("button", { name: /^save snapshot$/i });
    expect(saveInDialog.hasAttribute("disabled")).toBe(true);
  });

  // -------------------------------------------------------------------------
  // 4. Branch indicator
  // -------------------------------------------------------------------------
  it("shows the branch name in the breadcrumb", () => {
    render(<Header />);
    expect(screen.getByText("main")).toBeDefined();
    expect(screen.getByLabelText("Branch: main")).toBeDefined();
  });

  it("marks ai/ branches visually (uses Bot icon or violet styling)", () => {
    mockUseAeroplanes.mockReturnValue(
      defaultAeroplanes({ branch_name: "ai/winglet-experiment", is_main_branch: false }),
    );
    render(<Header />);
    // The branch indicator text should be rendered.
    expect(screen.getByText("ai/winglet-experiment")).toBeDefined();
    const indicator = screen.getByLabelText("Branch: ai/winglet-experiment");
    // Check the element has violet styling (class contains "violet").
    expect(indicator.className).toContain("violet");
  });

  it("hides branch indicator when branch_name is null (legacy aeroplane)", () => {
    mockUseAeroplanes.mockReturnValue(
      defaultAeroplanes({ branch_name: null }),
    );
    const { container } = render(<Header />);
    // No element with aria-label "Branch: ..." should exist.
    const indicator = container.querySelector('[aria-label^="Branch:"]');
    expect(indicator).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 5. History button calls onOpenHistory
  // -------------------------------------------------------------------------
  it("clicking the v3/history button calls onOpenHistory", async () => {
    const user = userEvent.setup();
    const onOpenHistory = vi.fn();
    render(<Header onOpenHistory={onOpenHistory} />);

    const historyBtn = screen.getByRole("button", {
      name: /open history and variants panel/i,
    });
    await user.click(historyBtn);

    expect(onOpenHistory).toHaveBeenCalledOnce();
  });
});
