import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return {
    Maximize2: icon,
    Minimize2: icon,
    Settings: icon,
    Wind: icon,
    Ruler: icon,
    Target: icon,
    Navigation: icon,
    Gauge: icon,
    AlertTriangle: icon,
    SlidersHorizontal: icon,
    Activity: icon,
    Loader2: icon,
    Plane: icon,
    TrendingUp: icon,
    Zap: icon,
    RefreshCw: icon,
  };
});

import { buildAnalysisRightSlot } from "@/components/workbench/AnalysisViewerPanel";

describe("buildAnalysisRightSlot (gh-575)", () => {
  it("returns null when neither point count nor run timestamp is present", () => {
    expect(buildAnalysisRightSlot(null, null, null)).toBeNull();
    expect(buildAnalysisRightSlot(null, undefined, undefined)).toBeNull();
  });

  it("renders only the points segment when no run timestamp", () => {
    const node = buildAnalysisRightSlot(42, null, null);
    expect(node).not.toBeNull();
    const { container } = render(<>{node}</>);
    expect(container.textContent).toBe("42 points");
  });

  it("renders only the last-run segment when no point count", () => {
    const t = new Date("2026-05-19T14:07:00Z");
    const node = buildAnalysisRightSlot(null, t, 1234);
    expect(node).not.toBeNull();
    const { container } = render(<>{node}</>);
    expect(container.textContent).toMatch(/Last run: \d\d:\d\d · 1234 ms/);
  });

  it("joins both segments with bullet separator when both present", () => {
    const t = new Date("2026-05-19T14:07:00Z");
    const node = buildAnalysisRightSlot(7, t, 950);
    expect(node).not.toBeNull();
    const { container } = render(<>{node}</>);
    expect(container.textContent).toMatch(/^7 points · Last run: \d\d:\d\d · 950 ms$/);
  });

  it("omits last-run segment when only the timestamp is present (duration missing)", () => {
    const t = new Date("2026-05-19T14:07:00Z");
    expect(buildAnalysisRightSlot(null, t, null)).toBeNull();
    expect(buildAnalysisRightSlot(null, t, undefined)).toBeNull();
  });
});
