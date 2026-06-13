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
  hints: [],
};

const EMPTY_DIFF: GeometryDiff = {
  wings: [],
  counts: { sectionsChanged: 0, sectionsAdded: 0, sectionsRemoved: 0 },
  hasAnyChange: false,
  hints: [],
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

// ---------------------------------------------------------------------------
// GH #972 — sub-element field sub-rows render under a flag
// ---------------------------------------------------------------------------

const DIFF_WITH_SPAR_FIELDS: GeometryDiff = {
  wings: [
    {
      name: "main_wing",
      kind: "changed",
      sections: [
        {
          index: 0,
          kind: "changed",
          label: "Section 1 · root",
          params: [],
          flags: [
            {
              key: "spar",
              kind: "changed",
              a: "1 spar",
              b: "1 spar",
              fields: [
                { key: "spar 1 position", a: "0.3", b: "0.4" },
                { key: "spar 1 width", a: "10 mm", b: "12 mm" },
              ],
            },
          ],
        },
      ],
    },
  ],
  counts: { sectionsChanged: 1, sectionsAdded: 0, sectionsRemoved: 0 },
  hasAnyChange: true,
  hints: [],
};

/** DIFF_WITH_HINTS: pre-computed hints embedded in the diff object (gh-973). */
const DIFF_WITH_HINTS: GeometryDiff = {
  wings: [
    {
      name: "main_wing",
      kind: "changed",
      sections: [
        {
          index: 0,
          kind: "changed",
          label: "Section 1 · root",
          params: [
            { key: "root chord", a: "200 mm", b: "200 mm" },
            { key: "tip chord", a: "150 mm", b: "100 mm" },
          ],
          flags: [],
        },
      ],
    },
  ],
  counts: { sectionsChanged: 1, sectionsAdded: 0, sectionsRemoved: 0 },
  hasAnyChange: true,
  hints: ["More taper (tip chord ↓)"],
};

describe("GeometryDiffSection — gh-972 sub-element field sub-rows", () => {
  beforeEach(() => {
    useGeometryDiffMock.mockReset();
  });

  it("renders spar field sub-rows beneath the flag row when expanded", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_SPAR_FIELDS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    // The spar flag row renders
    expect(screen.getByTestId("geometry-diff-row-spar")).toBeDefined();
    // Sub-rows render with testids for the fields
    expect(screen.getByTestId("geometry-diff-subrow-spar 1 position")).toBeDefined();
    expect(screen.getByTestId("geometry-diff-subrow-spar 1 width")).toBeDefined();
  });

  it("sub-row shows the from→to values", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_SPAR_FIELDS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const posRow = screen.getByTestId("geometry-diff-subrow-spar 1 position");
    const text = posRow.textContent ?? "";
    expect(text).toMatch(/0\.3/);
    expect(text).toMatch(/0\.4/);
  });

  it("sub-row is marked data-differs=true when values differ", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_SPAR_FIELDS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const posRow = screen.getByTestId("geometry-diff-subrow-spar 1 position");
    expect(posRow.getAttribute("data-differs")).toBe("true");
  });

  it("no sub-rows when flags have no fields array", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: CHANGED_DIFF }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    // CHANGED_DIFF has control_surface flag with no fields → no subrow testid present
    expect(screen.queryByTestId(/geometry-diff-subrow/)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// GH #973 — hint block renders with hedge text and aria attributes
// ---------------------------------------------------------------------------

describe("GeometryDiffSection — gh-973 hints block", () => {
  beforeEach(() => {
    useGeometryDiffMock.mockReset();
  });

  it("renders geometry-diff-hints block when hints are present + section expanded", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_HINTS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    expect(screen.getByTestId("geometry-diff-hints")).toBeDefined();
  });

  it("hint block has role='note'", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_HINTS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const hintsBlock = screen.getByTestId("geometry-diff-hints");
    expect(hintsBlock.getAttribute("role")).toBe("note");
  });

  it("hint block has aria-label='Geometry observations'", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_HINTS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const hintsBlock = screen.getByTestId("geometry-diff-hints");
    expect(hintsBlock.getAttribute("aria-label")).toBe("Geometry observations");
  });

  it("hint block contains the hedge prefix text", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_HINTS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const hintsBlock = screen.getByTestId("geometry-diff-hints");
    expect(hintsBlock.textContent ?? "").toMatch(/rough guide|verify with analysis/i);
  });

  it("hint block renders diff.hints (from the diff object, not derived separately)", () => {
    // DIFF_WITH_HINTS has hints: ["More taper (tip chord ↓)"] pre-computed
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_HINTS }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    const hintsBlock = screen.getByTestId("geometry-diff-hints");
    expect(hintsBlock.textContent ?? "").toMatch(/taper/i);
  });

  it("hint block is NOT rendered when diff.hints is empty", () => {
    // EMPTY_DIFF has hints: []
    useGeometryDiffMock.mockReturnValue(result({ diff: EMPTY_DIFF }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    expect(screen.queryByTestId("geometry-diff-hints")).toBeNull();
  });

  it("hint block is NOT rendered when section is collapsed", () => {
    useGeometryDiffMock.mockReturnValue(result({ diff: DIFF_WITH_HINTS }));
    render(<GeometryDiffSection {...PROPS} />);
    // do NOT click to expand
    expect(screen.queryByTestId("geometry-diff-hints")).toBeNull();
  });

  it("hints from diff with no change params shows no hint block (hints:[])", () => {
    const diffNoHints: GeometryDiff = {
      wings: [{ name: "main", kind: "changed", sections: [{ index: 0, kind: "changed", label: "Section 1 · root", params: [], flags: [] }] }],
      counts: { sectionsChanged: 1, sectionsAdded: 0, sectionsRemoved: 0 },
      hasAnyChange: true,
      hints: [],
    };
    useGeometryDiffMock.mockReturnValue(result({ diff: diffNoHints }));
    render(<GeometryDiffSection {...PROPS} />);
    fireEvent.click(screen.getByTestId("geometry-diff-header"));
    expect(screen.queryByTestId("geometry-diff-hints")).toBeNull();
  });
});
