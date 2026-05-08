import { describe, it, expect } from "vitest";
import { TABS } from "@/components/workbench/AnalysisViewerPanel";

describe("AnalysisViewerPanel TABS", () => {
  it("includes Stability in the tabs list", () => {
    expect(TABS).toContain("Stability");
  });

  it("has Stability as the last tab", () => {
    expect(TABS[TABS.length - 1]).toBe("Stability");
  });
});
