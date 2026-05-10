import { describe, it, expect } from "vitest";
import { TABS } from "@/components/workbench/AnalysisViewerPanel";

describe("AnalysisViewerPanel TABS", () => {
  it("includes Stability in the tabs list", () => {
    expect(TABS).toContain("Stability");
  });

  it("places Operating Points right after Assumptions", () => {
    const assumptionsIdx = TABS.indexOf("Assumptions");
    const opsIdx = TABS.indexOf("Operating Points");
    expect(assumptionsIdx).toBe(0);
    expect(opsIdx).toBe(assumptionsIdx + 1);
  });
});
