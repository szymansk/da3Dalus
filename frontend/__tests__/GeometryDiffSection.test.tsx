/**
 * Unit tests for GeometryDiffSection (gh-971).
 *
 * The section is a collapsible row under the metric compare sections. It owns
 * `expanded` + `showAll` state and delegates the lazy fetch+diff to
 * useGeometryDiff. We mock the hook so no network/SWR is involved and assert:
 *
 *  - collapsed by default: only the header renders, the hook is called with
 *    enabled=false (no fetch).
 *  - expanding flips the hook to enabled=true and renders the diff table.
 *  - loading shows a spinner.
 *  - an error renders an inline block (does NOT throw / crash the view).
 *  - "No geometry changes." when hasAnyChange is false.
 *  - changed param cell is amber (data-differs); from→to values shown.
 *  - added / removed section badges render with "—" on the empty side.
 *  - "Changes only / Show all" toggle flips the showAll arg to the hook.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";

import type { GeometryDiff } from "@/lib/geometryDiff";
import type { UseGeometryDiffResult } from "@/hooks/useGeometryDiff";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { "data-icon": "true", ...props });
  return { ChevronRight: icon, ChevronDown: icon, Loader2: icon };
});

const useGeometryDiffMock =
  vi.fn<(...args: unknown[]) => UseGeometryDiffResult>();
vi.mock("@/hooks/useGeometryDiff", () => ({
  useGeometryDiff: (...args: unknown[]) => useGeometryDiffMock(...args),
}));

import { GeometryDiffSection } from "../components/workbench/GeometryDiffSection";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const CHANGED_DIFF: GeometryDiff = {
  wings: [
    {
      name: "main_wing",
      kind: "changed",
      sections: [
        {
          index: 0,
          kind: "changed",
          label: "Section 1 · root",
          params: [{ key: "root chord", a: "162 mm", b: "158 mm" }],
          flags: [
            { key: "control_surface", kind: "changed", a: "—", b: "aileron" },
          ],
        },
        {
          index: 1,
          kind: "added",
          label: "Section 2 · mid",
          params: [],
          flags: [],
        },
        {
          index: 2,
          kind: "removed",
          label: "Section 3 · tip",
          params: [],
          flags: [],
        },
      ],
    },
  ],
  counts: { sectionsChanged: 1, sectionsAdded: 1, sectionsRemoved: 1 },
  hasAnyChange: true,
};

const EMPTY_DIFF: GeometryDiff = {
  wings: [],
  counts: { sectionsChanged: 0, sectionsAdded: 0, sectionsRemoved: 0 },
  hasAnyChange: false,
};

function result(over: Partial<UseGeometryDiffResult> = {}): UseGeometryDiffResult {
  return { diff: null, isLoading: false, error: null, ...over };
}

const PROPS = {
  nodeAUuid: "aaa",
  nodeBUuid: "bbb",
  wingNames: ["main_wing"],
  labelA: "Alpha",
  labelB: "Beta",
};

function renderSection(over: Partial<UseGeometryDiffResult> = {}) {
  useGeometryDiffMock.mockReturnValue(result(over));
  return render(<GeometryDiffSection {...PROPS} />);
}

describe("GeometryDiffSection (gh-971)", () => {
  beforeEach(() => {
    useGeometryDiffMock.mockReset();
  });

  // -------------------------------------------------------------------------
  // Collapsed by default — header only, no fetch
  // -------------------------------------------------------------------------
  it("renders the section testid", () => {
    renderSection();
    expect(screen.getByTestId("geometry-diff-section")).toBeDefined();
  });

  it("toggle button has aria-controls='geometry-diff-body'", () => {
    renderSection();
    const btn = screen.getByTestId("geometry-diff-header");
    expect(btn.getAttribute("aria-controls")).toBe("geometry-diff-body");
  });

  it("expanded body has id='geometry-diff-body'", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const body = document.getElementById("geometry-diff-body");
    expect(body).not.toBeNull();
  });

  it("is collapsed by default: the hook is called with enabled=false", () => {
    renderSection();
    // 4th positional arg = enabled
    const call = useGeometryDiffMock.mock.calls[0];
    expect(call[3]).toBe(false);
  });

  it("collapsed: does not render the diff table", () => {
    renderSection({ diff: CHANGED_DIFF, isLoading: false });
    expect(screen.queryByTestId("geometry-diff-table")).toBeNull();
  });

  it("shows the change counts in the header", () => {
    renderSection({ diff: CHANGED_DIFF });
    const header = screen.getByTestId("geometry-diff-header");
    const text = header.textContent ?? "";
    expect(text).toMatch(/1\s*changed/i);
    expect(text).toMatch(/1\s*added/i);
    expect(text).toMatch(/1\s*removed/i);
  });

  // -------------------------------------------------------------------------
  // Expanding triggers the lazy fetch (enabled=true) + renders table
  // -------------------------------------------------------------------------
  it("expanding flips the hook to enabled=true", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const lastCall =
      useGeometryDiffMock.mock.calls[useGeometryDiffMock.mock.calls.length - 1];
    expect(lastCall[3]).toBe(true);
  });

  it("expanding renders the diff table with the wing subheader", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    expect(screen.getByTestId("geometry-diff-table")).toBeDefined();
    expect(screen.getByText("main_wing")).toBeDefined();
  });

  it("expanded: renders a changed param row with from→to values and amber flag", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const row = screen.getByTestId("geometry-diff-row-root chord");
    expect(row.getAttribute("data-differs")).toBe("true");
    const text = row.textContent ?? "";
    expect(text).toMatch(/162 mm/);
    expect(text).toMatch(/158 mm/);
  });

  it("expanded: renders added and removed section badges", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const table = screen.getByTestId("geometry-diff-table");
    expect(within(table).getByText(/added/i)).toBeDefined();
    expect(within(table).getByText(/removed/i)).toBeDefined();
  });

  it("expanded: a sub-element flag with empty side shows '—'", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const row = screen.getByTestId("geometry-diff-row-control_surface");
    const text = row.textContent ?? "";
    expect(text).toMatch(/—/);
    expect(text).toMatch(/aileron/);
  });

  // -------------------------------------------------------------------------
  // Loading / error / empty states
  // -------------------------------------------------------------------------
  it("expanded + loading: shows a spinner and no table", () => {
    renderSection({ diff: null, isLoading: true });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    expect(screen.getByTestId("geometry-diff-loading")).toBeDefined();
    expect(screen.queryByTestId("geometry-diff-table")).toBeNull();
  });

  it("expanded + error: shows an inline error block and does not crash", () => {
    renderSection({ diff: null, error: new Error("boom") });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const err = screen.getByTestId("geometry-diff-error");
    expect(err).toBeDefined();
    expect(err.textContent ?? "").toMatch(/boom|could not|failed/i);
  });

  it("expanded + no changes: shows 'No geometry changes.'", () => {
    renderSection({ diff: EMPTY_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    expect(screen.getByText(/no geometry changes/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // Show-all toggle
  // -------------------------------------------------------------------------
  it("defaults to changes-only: the hook is called with showAll=false", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const lastCall =
      useGeometryDiffMock.mock.calls[useGeometryDiffMock.mock.calls.length - 1];
    // 5th positional arg = showAll
    expect(lastCall[4]).toBe(false);
  });

  it("toggling 'Show all' flips the showAll arg to the hook to true", () => {
    renderSection({ diff: CHANGED_DIFF });
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    fireEvent.click(screen.getByTestId("geometry-diff-showall-toggle"));
    const lastCall =
      useGeometryDiffMock.mock.calls[useGeometryDiffMock.mock.calls.length - 1];
    expect(lastCall[4]).toBe(true);
  });
});
