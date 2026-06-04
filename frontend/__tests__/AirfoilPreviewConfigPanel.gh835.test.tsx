/**
 * Tests for AirfoilPreviewConfigPanel gh-835 filter bar integration.
 *
 * Covers:
 * - Filter bar NOT rendered when suitabilityFilters prop is undefined
 * - Filter bar IS rendered when suitabilityFilters prop is provided
 * - Filter bar receives correct filters state
 * - Empty filter state shown when rootRankedMode is on + rootSortedNames is empty array
 * - onSuitabilityFiltersChange wires up to filter bar
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return {
    Info: icon, ArrowLeft: icon, Save: icon, Loader2: icon,
    ChevronLeft: icon, ChevronRight: icon, Undo2: icon,
    Search: icon, Check: icon, ChevronDown: icon, ChevronUp: icon,
  };
});

vi.mock("swr", () => ({
  default: () => ({ data: undefined, error: null, isLoading: false }),
}));
vi.mock("@/lib/fetcher", () => ({ fetcher: vi.fn() }));

import { AirfoilPreviewConfigPanel } from "@/components/workbench/AirfoilPreviewConfigPanel";
import { emptyFilters } from "@/components/workbench/AirfoilSuitabilityFilterBar";

const BASE_PROPS = {
  rootAirfoil: "naca0015",
  tipAirfoil: "naca0015",
  onRootAirfoilChange: vi.fn(),
  onTipAirfoilChange: vi.fn(),
  isRunning: false,
  segmentIndex: 0,
  segmentCount: 1,
  onSegmentChange: vi.fn(),
  segmentProps: {},
  velocity: 14,
  onVelocityChange: vi.fn(),
  rootRe: 200000,
  tipRe: 150000,
  onRootReChange: vi.fn(),
  onTipReChange: vi.fn(),
  rootChordMm: 200,
  tipChordMm: 150,
  isDirty: false,
  isSaving: false,
  onSave: vi.fn(),
  onRevert: vi.fn(),
  onBack: vi.fn(),
};

describe("AirfoilPreviewConfigPanel — gh-835 filter bar", () => {
  it("does NOT render filter bar when suitabilityFilters is undefined", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    expect(screen.queryByTestId("suitability-filter-bar")).toBeNull();
  });

  it("renders filter bar when suitabilityFilters is provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        suitabilityFilters={emptyFilters()}
        onSuitabilityFiltersChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("suitability-filter-bar")).toBeInTheDocument();
  });

  it("passes onFiltersChange callback to filter bar (clear button triggers it)", () => {
    const onChange = vi.fn();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        suitabilityFilters={{ ...emptyFilters(), families: ["reflexed"] }}
        onSuitabilityFiltersChange={onChange}
      />,
    );
    // Clear button should be visible because families is non-empty
    const clearBtn = screen.getByTestId("filter-clear-btn");
    fireEvent.click(clearBtn);
    expect(onChange).toHaveBeenCalledWith(emptyFilters());
  });

  it("does NOT render empty-state notice when ranked mode off", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootRankedMode={false}
        rootSortedNames={[]}
      />,
    );
    expect(screen.queryByTestId("filter-empty-state-root")).toBeNull();
  });

  it("renders empty-state notice when rootRankedMode=true AND rootSortedNames is empty", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootRankedMode
        rootSortedNames={[]}
        onRootRankedModeToggle={vi.fn()}
      />,
    );
    expect(screen.getByTestId("filter-empty-state-root")).toBeInTheDocument();
    expect(screen.getByText(/Keine Profile passen zu den Filtern/)).toBeInTheDocument();
  });

  it("does NOT render empty-state when rootSortedNames has entries", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootRankedMode
        rootSortedNames={["naca0015", "naca2412"]}
        onRootRankedModeToggle={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("filter-empty-state-root")).toBeNull();
  });
});
