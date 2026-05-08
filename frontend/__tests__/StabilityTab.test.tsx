import { describe, it, expect } from "vitest";
import { TABS } from "@/components/workbench/AnalysisViewerPanel";

describe("AnalysisViewerPanel TABS", () => {
  it("includes Stability in the tabs list", () => {
    expect(TABS).toContain("Stability");
  });

  it("includes Stability before Operating Points", () => {
    const stabilityIdx = TABS.indexOf("Stability");
    const opsIdx = TABS.indexOf("Operating Points");
    expect(stabilityIdx).toBeGreaterThan(-1);
    expect(opsIdx).toBeGreaterThan(stabilityIdx);
  });
});
