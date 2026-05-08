/**
 * Unit tests for the AnalysisStatusIndicator component.
 *
 * Tests all visual states: empty, all trimmed, dirty, computing,
 * debouncing.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import type { AnalysisStatus } from "@/hooks/useAnalysisStatus";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": "loader-icon" });
  return {
    Loader2: icon,
  };
});

function makeStatus(overrides: Partial<AnalysisStatus> = {}): AnalysisStatus {
  return {
    op_counts: {},
    total_ops: 0,
    retrim_active: false,
    retrim_debouncing: false,
    last_computation: null,
    ...overrides,
  };
}

async function loadComponent() {
  const mod = await import(
    "@/components/workbench/AnalysisStatusIndicator"
  );
  return mod.AnalysisStatusIndicator;
}

describe("AnalysisStatusIndicator", () => {
  it("renders nothing when total_ops is 0", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({ total_ops: 0 });
    const { container } = render(<AnalysisStatusIndicator status={status} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders 'All trimmed' when all OPs are TRIMMED", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { TRIMMED: 5 },
      total_ops: 5,
    });
    render(<AnalysisStatusIndicator status={status} />);
    expect(screen.getByText("All trimmed")).toBeInTheDocument();
    // Verify green styling
    const span = screen.getByText("All trimmed");
    expect(span.className).toMatch(/emerald/);
  });

  it("renders dirty count when DIRTY OPs exist", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { DIRTY: 3, TRIMMED: 2 },
      total_ops: 5,
    });
    render(<AnalysisStatusIndicator status={status} />);
    expect(screen.getByText("3 points outdated")).toBeInTheDocument();
    const span = screen.getByText("3 points outdated");
    expect(span.className).toMatch(/orange/);
  });

  it("renders singular 'point' for 1 dirty OP", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { DIRTY: 1, TRIMMED: 4 },
      total_ops: 5,
    });
    render(<AnalysisStatusIndicator status={status} />);
    expect(screen.getByText("1 point outdated")).toBeInTheDocument();
  });

  it("renders spinner when COMPUTING OPs exist", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { COMPUTING: 2, TRIMMED: 3 },
      total_ops: 5,
    });
    render(<AnalysisStatusIndicator status={status} />);
    // Should show re-trimming message with progress
    expect(screen.getByText(/Re-trimming 3\/5/)).toBeInTheDocument();
    // Spinner icon should be present
    expect(screen.getByTestId("loader-icon")).toBeInTheDocument();
  });

  it("renders spinner when retrim_active is true", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { TRIMMED: 3 },
      total_ops: 5,
      retrim_active: true,
    });
    render(<AnalysisStatusIndicator status={status} />);
    expect(screen.getByText(/Re-trimming 3\/5/)).toBeInTheDocument();
    expect(screen.getByTestId("loader-icon")).toBeInTheDocument();
  });

  it("renders 'Waiting for changes' when debouncing", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { TRIMMED: 5 },
      total_ops: 5,
      retrim_debouncing: true,
    });
    render(<AnalysisStatusIndicator status={status} />);
    expect(screen.getByText(/Waiting for changes/)).toBeInTheDocument();
    const span = screen.getByText(/Waiting for changes/);
    expect(span.className).toMatch(/zinc/);
  });

  it("prefers computing state over dirty state", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { COMPUTING: 1, DIRTY: 2, TRIMMED: 2 },
      total_ops: 5,
    });
    render(<AnalysisStatusIndicator status={status} />);
    // Computing takes priority
    expect(screen.getByText(/Re-trimming/)).toBeInTheDocument();
    expect(screen.queryByText(/outdated/)).not.toBeInTheDocument();
  });

  it("prefers computing over debouncing", async () => {
    const AnalysisStatusIndicator = await loadComponent();
    const status = makeStatus({
      op_counts: { COMPUTING: 1, TRIMMED: 4 },
      total_ops: 5,
      retrim_debouncing: true,
    });
    render(<AnalysisStatusIndicator status={status} />);
    expect(screen.getByText(/Re-trimming/)).toBeInTheDocument();
    expect(screen.queryByText(/Waiting/)).not.toBeInTheDocument();
  });
});
