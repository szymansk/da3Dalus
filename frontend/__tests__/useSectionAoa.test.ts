/**
 * Unit tests for useSectionAoa hook helpers (gh-840).
 *
 * Strategy: test the pure helper functions (findSectionAtFraction,
 * sectionForXsecIndex) without mocking SWR — these carry the critical
 * business logic (section selection from spanwise fraction).
 */
import { describe, it, expect } from "vitest";
import { findSectionAtFraction, sectionForXsecIndex } from "@/hooks/useSectionAoa";
import type { SectionAoaPoint } from "@/hooks/useSectionAoa";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSection(y_m: number, alpha_effective_deg: number): SectionAoaPoint {
  return {
    y_m,
    chord_m: 0.2,
    cl: 0.7,
    alpha_geometric_deg: alpha_effective_deg + 1.5,
    alpha_effective_deg,
    induced_angle_deg: 1.5,
  };
}

const SAMPLE_SECTIONS: SectionAoaPoint[] = [
  makeSection(-0.45, 4.5), // negative y (port)
  makeSection(-0.25, 4.8),
  makeSection(-0.05, 5.1),
  makeSection(0.05, 5.1),  // positive y (starboard)
  makeSection(0.25, 4.8),
  makeSection(0.45, 4.5),
];

// ---------------------------------------------------------------------------
// findSectionAtFraction
// ---------------------------------------------------------------------------

describe("findSectionAtFraction", () => {
  it("returns null for empty sections", () => {
    expect(findSectionAtFraction([], 0.5)).toBeNull();
  });

  it("returns the root section (fraction=0) for positive y=0.05", () => {
    const result = findSectionAtFraction(SAMPLE_SECTIONS, 0);
    // Closest positive-y section to y=0 is 0.05
    expect(result).not.toBeNull();
    expect(result!.y_m).toBeCloseTo(0.05, 2);
  });

  it("returns the tip section (fraction=1) for positive y=0.45", () => {
    const result = findSectionAtFraction(SAMPLE_SECTIONS, 1);
    expect(result).not.toBeNull();
    expect(result!.y_m).toBeCloseTo(0.45, 2);
  });

  it("returns midspan section (fraction=0.5) closest to y=0.225", () => {
    const result = findSectionAtFraction(SAMPLE_SECTIONS, 0.5);
    expect(result).not.toBeNull();
    // y=0.225 → closest to 0.25
    expect(result!.y_m).toBeCloseTo(0.25, 2);
  });

  it("only considers positive-y sections for symmetric wing", () => {
    const result = findSectionAtFraction(SAMPLE_SECTIONS, 0.5);
    expect(result!.y_m).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// sectionForXsecIndex
// ---------------------------------------------------------------------------

describe("sectionForXsecIndex", () => {
  it("returns null for empty sections", () => {
    expect(sectionForXsecIndex([], 0, 3)).toBeNull();
  });

  it("returns root section for xsec=0 of 3 segments (fraction=0)", () => {
    const result = sectionForXsecIndex(SAMPLE_SECTIONS, 0, 3);
    expect(result).not.toBeNull();
    expect(result!.y_m).toBeGreaterThanOrEqual(0);
  });

  it("returns tip section for xsec=2 of 3 segments (fraction=1)", () => {
    const result = sectionForXsecIndex(SAMPLE_SECTIONS, 2, 3);
    expect(result).not.toBeNull();
    expect(result!.y_m).toBeCloseTo(0.45, 2);
  });

  it("returns root for single-segment wing (segmentCount=1)", () => {
    const result = sectionForXsecIndex(SAMPLE_SECTIONS, 0, 1);
    expect(result).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// as-built alpha extraction
// ---------------------------------------------------------------------------

describe("alpha_effective_deg extraction", () => {
  it("the as-built alpha is alpha_effective_deg from the selected section", () => {
    // Simulate what the page does: pick section, read alpha_effective_deg
    const section = sectionForXsecIndex(SAMPLE_SECTIONS, 2, 3);
    expect(section?.alpha_effective_deg).toBeCloseTo(4.5, 1);
  });
});
