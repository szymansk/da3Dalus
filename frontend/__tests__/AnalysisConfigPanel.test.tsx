/**
 * gh-787: numeric inputs in the analysis config panel must keep a
 * user-entered 0 (finiteOr) instead of the old `parseFloat || default`
 * idiom that silently rewrote 0 → default.
 *
 * Also covers the three run handlers (Polar / Trefftz strip-forces /
 * Streamlines) so the changed call-sites are exercised.
 */
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return {
    Play: icon,
    RefreshCw: icon,
    ChevronDown: icon,
    ChevronRight: icon,
    Loader2: icon,
  };
});

import { AnalysisConfigPanel } from "@/components/workbench/AnalysisConfigPanel";

function makeAnalysis(overrides: Record<string, unknown> = {}) {
  return {
    isRunning: false,
    error: null,
    runAlphaSweep: vi.fn(),
    ...overrides,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any;
}

const BASE = {
  wingNames: ["Wing"] as string[],
  selectedWing: "Wing" as string | null,
  onClose: vi.fn(),
};

function runButton() {
  return screen.getByRole("button", { name: /Run Analysis/i });
}

describe("AnalysisConfigPanel numeric inputs (gh-787)", () => {
  it("keeps a sweep start of 0 instead of falling back to -5", () => {
    const analysis = makeAnalysis();
    render(<AnalysisConfigPanel activeTab="Polar" analysis={analysis} {...BASE} />);

    fireEvent.change(screen.getByLabelText("start"), { target: { value: "0" } });
    fireEvent.click(runButton());

    expect(analysis.runAlphaSweep).toHaveBeenCalledTimes(1);
    expect(analysis.runAlphaSweep.mock.calls[0][0]).toMatchObject({ alpha_start: 0 });
  });

  it("still falls back to -5 when the start field is cleared", () => {
    const analysis = makeAnalysis();
    render(<AnalysisConfigPanel activeTab="Polar" analysis={analysis} {...BASE} />);

    fireEvent.change(screen.getByLabelText("start"), { target: { value: "" } });
    fireEvent.click(runButton());

    expect(analysis.runAlphaSweep.mock.calls[0][0]).toMatchObject({ alpha_start: -5 });
  });

  it("runs strip forces from the Trefftz Plane tab", () => {
    const analysis = makeAnalysis();
    const onRunStripForces = vi.fn();
    render(
      <AnalysisConfigPanel
        activeTab="Trefftz Plane"
        analysis={analysis}
        onRunStripForces={onRunStripForces}
        {...BASE}
      />,
    );

    fireEvent.click(runButton());
    expect(onRunStripForces).toHaveBeenCalledTimes(1);
    // default velocity 14 is finite → kept
    expect(onRunStripForces.mock.calls[0][0]).toMatchObject({ velocity: 14, beta: 0 });
  });

  it("runs streamlines from the Streamlines tab", () => {
    const analysis = makeAnalysis();
    const onRunStreamlines = vi.fn();
    render(
      <AnalysisConfigPanel
        activeTab="Streamlines"
        analysis={analysis}
        onRunStreamlines={onRunStreamlines}
        {...BASE}
      />,
    );

    fireEvent.click(runButton());
    expect(onRunStreamlines).toHaveBeenCalledTimes(1);
    expect(onRunStreamlines.mock.calls[0][0]).toMatchObject({ beta: 0 });
  });
});
