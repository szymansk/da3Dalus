/**
 * Tests for AirfoilSuitabilityFilterBar (gh-835).
 *
 * Covers:
 * - Render: all chip groups and thickness inputs present
 * - Family chip toggles update `families` in filters
 * - Tag chip toggles update `tags` in filters
 * - Thickness inputs update `thicknessMinPct` / `thicknessMaxPct`
 * - Clear button shown only when filters are non-empty, resets to empty
 * - Empty filter state (no clear button)
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import {
  AirfoilSuitabilityFilterBar,
  emptyFilters,
  isFiltersEmpty,
} from "@/components/workbench/AirfoilSuitabilityFilterBar";
import type { AirfoilSuitabilityFilters } from "@/components/workbench/AirfoilSuitabilityFilterBar";

function empty(): AirfoilSuitabilityFilters {
  return emptyFilters();
}

describe("AirfoilSuitabilityFilterBar", () => {
  it("renders the filter bar container", () => {
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={() => {}} />,
    );
    expect(screen.getByTestId("suitability-filter-bar")).toBeInTheDocument();
  });

  it("renders family chips (all 5)", () => {
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={() => {}} />,
    );
    expect(screen.getByTestId("chip-flat_bottom")).toBeInTheDocument();
    expect(screen.getByTestId("chip-semi_symmetric")).toBeInTheDocument();
    expect(screen.getByTestId("chip-symmetric")).toBeInTheDocument();
    expect(screen.getByTestId("chip-cambered")).toBeInTheDocument();
    expect(screen.getByTestId("chip-reflexed")).toBeInTheDocument();
  });

  it("renders role-tag chips (all 6)", () => {
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={() => {}} />,
    );
    expect(screen.getByTestId("chip-winglet")).toBeInTheDocument();
    expect(screen.getByTestId("chip-h_stabilizer")).toBeInTheDocument();
    expect(screen.getByTestId("chip-v_stabilizer")).toBeInTheDocument();
    expect(screen.getByTestId("chip-acro")).toBeInTheDocument();
    expect(screen.getByTestId("chip-low_re")).toBeInTheDocument();
    expect(screen.getByTestId("chip-high_re")).toBeInTheDocument();
  });

  it("renders thickness inputs", () => {
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={() => {}} />,
    );
    expect(screen.getByTestId("thickness-min-input")).toBeInTheDocument();
    expect(screen.getByTestId("thickness-max-input")).toBeInTheDocument();
  });

  it("does NOT show clear button when filters are empty", () => {
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={() => {}} />,
    );
    expect(screen.queryByTestId("filter-clear-btn")).toBeNull();
  });

  it("shows clear button when family filter is active", () => {
    render(
      <AirfoilSuitabilityFilterBar
        filters={{ ...empty(), families: ["reflexed"] }}
        onFiltersChange={() => {}}
      />,
    );
    expect(screen.getByTestId("filter-clear-btn")).toBeInTheDocument();
  });

  it("shows clear button when tag filter is active", () => {
    render(
      <AirfoilSuitabilityFilterBar
        filters={{ ...empty(), tags: ["acro"] }}
        onFiltersChange={() => {}}
      />,
    );
    expect(screen.getByTestId("filter-clear-btn")).toBeInTheDocument();
  });

  it("clicking clear button calls onFiltersChange with emptyFilters()", () => {
    const onChange = vi.fn();
    render(
      <AirfoilSuitabilityFilterBar
        filters={{ ...empty(), families: ["reflexed"] }}
        onFiltersChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("filter-clear-btn"));
    expect(onChange).toHaveBeenCalledWith(emptyFilters());
  });

  it("clicking a family chip adds it to families", () => {
    const onChange = vi.fn();
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={onChange} />,
    );
    fireEvent.click(screen.getByTestId("chip-reflexed"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ families: ["reflexed"] }),
    );
  });

  it("clicking an active family chip removes it", () => {
    const onChange = vi.fn();
    render(
      <AirfoilSuitabilityFilterBar
        filters={{ ...empty(), families: ["reflexed"] }}
        onFiltersChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("chip-reflexed"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ families: [] }),
    );
  });

  it("clicking a tag chip adds it to tags", () => {
    const onChange = vi.fn();
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={onChange} />,
    );
    fireEvent.click(screen.getByTestId("chip-acro"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ tags: ["acro"] }),
    );
  });

  it("thickness min input calls onChange with updated value", () => {
    const onChange = vi.fn();
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={onChange} />,
    );
    fireEvent.change(screen.getByTestId("thickness-min-input"), {
      target: { value: "8" },
    });
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ thicknessMinPct: "8" }),
    );
  });

  it("thickness max input calls onChange with updated value", () => {
    const onChange = vi.fn();
    render(
      <AirfoilSuitabilityFilterBar filters={empty()} onFiltersChange={onChange} />,
    );
    fireEvent.change(screen.getByTestId("thickness-max-input"), {
      target: { value: "14" },
    });
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ thicknessMaxPct: "14" }),
    );
  });
});

// ── emptyFilters() and isFiltersEmpty() helpers ────────────────────────────

describe("emptyFilters", () => {
  it("returns object with empty arrays and empty strings", () => {
    const f = emptyFilters();
    expect(f.families).toEqual([]);
    expect(f.tags).toEqual([]);
    expect(f.thicknessMinPct).toBe("");
    expect(f.thicknessMaxPct).toBe("");
  });
});

describe("isFiltersEmpty", () => {
  it("returns true for emptyFilters()", () => {
    expect(isFiltersEmpty(emptyFilters())).toBe(true);
  });

  it("returns false when families is non-empty", () => {
    expect(isFiltersEmpty({ ...emptyFilters(), families: ["reflexed"] })).toBe(false);
  });

  it("returns false when tags is non-empty", () => {
    expect(isFiltersEmpty({ ...emptyFilters(), tags: ["acro"] })).toBe(false);
  });

  it("returns false when thicknessMinPct is set", () => {
    expect(isFiltersEmpty({ ...emptyFilters(), thicknessMinPct: "8" })).toBe(false);
  });

  it("returns false when thicknessMaxPct is set", () => {
    expect(isFiltersEmpty({ ...emptyFilters(), thicknessMaxPct: "14" })).toBe(false);
  });
});
