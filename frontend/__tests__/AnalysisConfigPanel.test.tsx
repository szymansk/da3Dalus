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

describe("AnalysisConfigPanel Spanwise Loads tab (gh-1002)", () => {
  it("renders the spanwise-loads config inputs", () => {
    render(
      <AnalysisConfigPanel
        activeTab="Spanwise Loads"
        analysis={makeAnalysis()}
        {...BASE}
      />,
    );

    expect(screen.getByLabelText("alpha")).toBeTruthy();
    expect(screen.getByLabelText("velocity")).toBeTruthy();
    expect(screen.getByLabelText("altitude")).toBeTruthy();
  });

  it("runs spanwise loads with the configured operating-point params", () => {
    const onRunSpanwiseLoads = vi.fn();
    render(
      <AnalysisConfigPanel
        activeTab="Spanwise Loads"
        analysis={makeAnalysis()}
        onRunSpanwiseLoads={onRunSpanwiseLoads}
        {...BASE}
      />,
    );

    fireEvent.click(runButton());

    expect(onRunSpanwiseLoads).toHaveBeenCalledTimes(1);
    // Defaults: velocity 14, alpha 5, beta 0, altitude 100 (all finite → kept).
    expect(onRunSpanwiseLoads.mock.calls[0][0]).toMatchObject({
      velocity: 14,
      alpha: 5,
      beta: 0,
      altitude: 100,
    });
  });

  it("disables the run button while spanwise loads are running (getIsRunning)", () => {
    render(
      <AnalysisConfigPanel
        activeTab="Spanwise Loads"
        analysis={makeAnalysis()}
        spanwiseLoadsRunning={true}
        {...BASE}
      />,
    );

    // While running the label switches to "Running…" and the button is disabled.
    const btn = screen.getByRole("button", { name: /Running/ });
    expect(btn.hasAttribute("disabled")).toBe(true);
  });

  it("surfaces a spanwise-loads error message (getCurrentError)", () => {
    render(
      <AnalysisConfigPanel
        activeTab="Spanwise Loads"
        analysis={makeAnalysis()}
        spanwiseLoadsError="Spanwise loads — invalid request: bad OP"
        {...BASE}
      />,
    );

    expect(
      screen.getByText(/Spanwise loads — invalid request: bad OP/),
    ).toBeTruthy();
  });
});

describe("AnalysisConfigPanel honest Polar selectors (gh-786)", () => {
  it("no longer renders the decorative sweep_var / solver / flight-profile selectors", () => {
    render(<AnalysisConfigPanel activeTab="Polar" analysis={makeAnalysis()} {...BASE} />);

    // sweep_var (alpha/beta/velocity) select removed — alpha is the only sweep
    expect(screen.queryByLabelText("sweep_var")).toBeNull();
    // solver picker + flight-profile select + the whole card removed
    expect(screen.queryByText("Analysis Tool")).toBeNull();
    expect(screen.queryByLabelText("Flight profile")).toBeNull();
    // the misleading footer claim is gone too
    expect(screen.queryByText(/AVL: single point only/i)).toBeNull();
  });

  it("Single Point mode runs a genuine 1-point evaluation (alpha_num=1)", () => {
    const analysis = makeAnalysis();
    render(<AnalysisConfigPanel activeTab="Polar" analysis={analysis} {...BASE} />);

    // switch to Single Point (first radio) and set the single α
    fireEvent.click(screen.getAllByRole("radio")[0]);
    fireEvent.change(screen.getByLabelText("alpha"), { target: { value: "6" } });
    fireEvent.click(runButton());

    expect(analysis.runAlphaSweep).toHaveBeenCalledTimes(1);
    expect(analysis.runAlphaSweep.mock.calls[0][0]).toMatchObject({
      alpha_start: 6,
      alpha_end: 6,
      alpha_num: 1,
    });
  });

  it("Parameter Sweep mode still produces a multi-point sweep", () => {
    const analysis = makeAnalysis();
    render(<AnalysisConfigPanel activeTab="Polar" analysis={analysis} {...BASE} />);

    // default mode is sweep; defaults -5..15 step 1 → 21 points
    fireEvent.click(runButton());
    const call = analysis.runAlphaSweep.mock.calls[0][0];
    expect(call.alpha_num).toBeGreaterThan(1);
  });

  it("activates Single Point via keyboard (ModeRadio onKeyDown)", () => {
    render(<AnalysisConfigPanel activeTab="Polar" analysis={makeAnalysis()} {...BASE} />);

    // default sweep → range "start" shown, no single "alpha"
    expect(screen.queryByLabelText("alpha")).toBeNull();
    fireEvent.keyDown(screen.getAllByRole("radio")[0], { key: "Enter" });
    // single mode now → single-alpha input present, range gone
    expect(screen.getByLabelText("alpha")).toBeTruthy();
    expect(screen.queryByLabelText("start")).toBeNull();
  });

  it("Reset to defaults restores the sweep start (and resets single α) without crashing", () => {
    const analysis = makeAnalysis();
    render(<AnalysisConfigPanel activeTab="Polar" analysis={analysis} {...BASE} />);

    fireEvent.change(screen.getByLabelText("start"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: /Reset to defaults/i }));
    fireEvent.click(runButton());

    expect(analysis.runAlphaSweep.mock.calls[0][0]).toMatchObject({ alpha_start: -5 });
  });
});
