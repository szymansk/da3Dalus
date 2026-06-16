import { describe, it, expect } from "vitest";
import { TABS } from "@/components/workbench/AnalysisViewerPanel";

// Regression guard for gh-567: the Stability tab has been removed from the
// Analysis view. Stability visualisation now lives in the construction-preview
// overlay (gh-569). The footer's neutral-point chip still uses the backend
// stability_service via assumption_compute_service, but no in-Analysis tab.
describe("AnalysisViewerPanel TABS (gh-567)", () => {
  it("does NOT include 'Stability' in the analysis tab list", () => {
    expect(TABS).not.toContain("Stability");
  });

  it("places Operating Points right after Assumptions", () => {
    const assumptionsIdx = TABS.indexOf("Assumptions");
    const opsIdx = TABS.indexOf("Operating Points");
    expect(assumptionsIdx).toBe(0);
    expect(opsIdx).toBe(assumptionsIdx + 1);
  });

  it("exposes the expected analysis tabs", () => {
    expect(TABS).toEqual([
      "Assumptions",
      "Operating Points",
      "Polar",
      "Trefftz Plane",
      "Spanwise Loads",
      "Streamlines",
      "Envelope",
      "Sizing",
    ]);
  });

  it("includes Spanwise Loads tab (gh-1002)", () => {
    expect(TABS).toContain("Spanwise Loads");
  });
});
