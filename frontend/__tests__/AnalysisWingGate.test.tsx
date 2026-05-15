import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
  };
});

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: () => ({ data: null, isLoading: false }),
}));

vi.mock("@/hooks/useDesignAssumptions", () => ({
  useDesignAssumptions: () => ({ data: null, isLoading: false }),
}));

describe("Analysis Tab Wing Gate", () => {
  it("shows empty state for Polar tab when hasWings is false", async () => {
    const mod = await import("@/components/workbench/AnalysisViewerPanel");
    const Panel = mod.AnalysisViewerPanel;

    render(
      <Panel
        result={null}
        activeTab="Polar"
        onTabChange={() => {}}
        hasWings={false}
        wingXSecs={null}
      />,
    );

    expect(screen.getByText(/add a wing/i)).toBeInTheDocument();
  });

  it("shows Assumptions tab content even when hasWings is false", async () => {
    const mod = await import("@/components/workbench/AnalysisViewerPanel");
    const Panel = mod.AnalysisViewerPanel;

    render(
      <Panel
        result={null}
        activeTab="Assumptions"
        onTabChange={() => {}}
        hasWings={false}
        wingXSecs={null}
      />,
    );

    expect(screen.queryByText(/add a wing/i)).not.toBeInTheDocument();
  });

  it("shows Polar content when hasWings is true", async () => {
    const mod = await import("@/components/workbench/AnalysisViewerPanel");
    const Panel = mod.AnalysisViewerPanel;

    render(
      <Panel
        result={null}
        activeTab="Polar"
        onTabChange={() => {}}
        hasWings={true}
        wingXSecs={null}
      />,
    );

    expect(screen.queryByText(/add a wing/i)).not.toBeInTheDocument();
  });
});
