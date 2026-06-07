/**
 * Unit tests for VersionCompareView (gh-907 — compare mode).
 *
 * Covered:
 * 1. Renders node labels for both variants (A and B).
 * 2. Renders key metric rows (V_cruise, AR, SM, (L/D)_max).
 * 3. A metric that differs between A and B is marked with data-differs="true".
 * 4. A metric that is equal in A and B does NOT have data-differs="true".
 * 5. Loading state shows a loading message.
 * 6. Error state shows the error text.
 * 7. Close button calls onClose.
 * 8. Renders gracefully when metrics_a / metrics_b are null (no crash).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { "data-icon": "true", ...props });
  return { X: icon, ArrowLeftRight: icon };
});

// metricsAdapters — use REAL adapters (not mocked); they are pure functions.
// renderSymbol — use real implementation.

// ---------------------------------------------------------------------------
// Lazy imports (after mock hoisting)
// ---------------------------------------------------------------------------

import { VersionCompareView } from "../components/workbench/VersionCompareView";
import type { CompareOut, VersionNode } from "@/types/versioning";
import type { ComputationContext } from "@/hooks/useComputationContext";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BASE_NODE_A: VersionNode = {
  id: 10,
  uuid: "aaa",
  name: "Plane A",
  branch_id: 1,
  predecessor_id: null,
  root_id: 10,
  is_immutable: false,
  version_label: "Alpha build",
  version_note: "Initial build",
  created_by: "human",
  provenance_message_id: null,
  preview_png: null,
  created_at: "2026-06-07T10:00:00Z",
  updated_at: "2026-06-07T10:00:00Z",
};

const BASE_NODE_B: VersionNode = {
  id: 20,
  uuid: "bbb",
  name: "Plane B",
  branch_id: 2,
  predecessor_id: 10,
  root_id: 10,
  is_immutable: true,
  version_label: "Winglet variant",
  version_note: "Wider winglets",
  created_by: "ai",
  provenance_message_id: null,
  preview_png: null,
  created_at: "2026-06-08T09:00:00Z",
  updated_at: "2026-06-08T09:00:00Z",
};

/** A minimal ComputationContext with enough fields for the adapters. */
function makeCtx(overrides: Partial<ComputationContext> = {}): ComputationContext {
  return {
    v_cruise_mps: 15.0,
    v_stall_mps: 9.0,
    v_md_mps: 12.5,
    v_max_mps: 22.0,
    reynolds: 2.5e5,
    mac_m: 0.25,
    s_ref_m2: 0.4,
    b_ref_m: 1.8,
    aspect_ratio: 8.1,
    cd0: 0.025,
    e_oswald: 0.82,
    e_oswald_fallback_used: false,
    x_np_m: 0.115,
    target_static_margin: 0.10,
    cg_agg_m: 0.088,
    is_glider: false,
    is_tailless: false,
    computed_at: "2026-06-07T10:00:00Z",
    polar_by_config: {
      clean: {
        cd0: 0.025,
        e_oswald: 0.82,
        cl_max: 1.2,
        e_oswald_r2: 0.98,
        e_oswald_quality: "high",
        flap_deflection_deg: 0,
        provenance: "aerobuildup",
        rejection: null,
        ld_max: 14.2,
        cl_at_ld_max: 0.55,
        e_oswald_provenance: "aerobuildup_trefftz",
      },
      takeoff: {
        cd0: 0.040,
        e_oswald: 0.82,
        cl_max: 1.5,
        e_oswald_r2: null,
        e_oswald_quality: "unknown",
        flap_deflection_deg: 15,
        provenance: "aerobuildup",
        rejection: null,
      },
      landing: {
        cd0: 0.055,
        e_oswald: 0.82,
        cl_max: 1.7,
        e_oswald_r2: null,
        e_oswald_quality: "unknown",
        flap_deflection_deg: 30,
        provenance: "aerobuildup",
        rejection: null,
      },
    },
    ...overrides,
  };
}

function makeCompareOut(
  metricsA: ComputationContext | null,
  metricsB: ComputationContext | null,
): CompareOut {
  return {
    node_a: BASE_NODE_A,
    node_b: BASE_NODE_B,
    metrics_a: metricsA as Record<string, unknown> | null,
    metrics_b: metricsB as Record<string, unknown> | null,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("VersionCompareView (gh-907)", () => {
  // -------------------------------------------------------------------------
  // 1. Renders node labels for both variants
  // -------------------------------------------------------------------------
  it("renders node labels for variant A and variant B", () => {
    const compareOut = makeCompareOut(makeCtx(), makeCtx());
    render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getAllByText("Alpha build").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Winglet variant").length).toBeGreaterThan(0);
  });

  it("shows snapshot badge on immutable node B", () => {
    const compareOut = makeCompareOut(makeCtx(), makeCtx());
    render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getAllByText("snapshot").length).toBeGreaterThan(0);
  });

  it("shows ai badge on node created by ai", () => {
    const compareOut = makeCompareOut(makeCtx(), makeCtx());
    render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getAllByText("ai").length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // 2. Renders key metric rows
  // -------------------------------------------------------------------------
  it("renders a metric row for V_cruise", () => {
    const compareOut = makeCompareOut(makeCtx(), makeCtx());
    const { container } = render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );
    const row = container.querySelector('[data-testid="compare-row-V_cruise"]');
    expect(row).not.toBeNull();
  });

  it("renders a metric row for AR", () => {
    const compareOut = makeCompareOut(makeCtx(), makeCtx());
    const { container } = render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );
    const row = container.querySelector('[data-testid="compare-row-AR"]');
    expect(row).not.toBeNull();
  });

  // -------------------------------------------------------------------------
  // 3. A metric that differs between A and B is flagged
  // -------------------------------------------------------------------------
  it("marks V_cruise row with data-differs=true when the two speeds differ", () => {
    // A: V_cruise = 15.0; B: V_cruise = 20.0
    const ctxA = makeCtx({ v_cruise_mps: 15.0 });
    const ctxB = makeCtx({ v_cruise_mps: 20.0 });
    const compareOut = makeCompareOut(ctxA, ctxB);

    const { container } = render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );

    const row = container.querySelector('[data-testid="compare-row-V_cruise"]');
    expect(row).not.toBeNull();
    expect(row?.getAttribute("data-differs")).toBe("true");
  });

  // -------------------------------------------------------------------------
  // 4. Equal values do NOT have data-differs
  // -------------------------------------------------------------------------
  it("does NOT mark V_cruise row as differs when both speeds are equal", () => {
    const ctxA = makeCtx({ v_cruise_mps: 15.0 });
    const ctxB = makeCtx({ v_cruise_mps: 15.0 });
    const compareOut = makeCompareOut(ctxA, ctxB);

    const { container } = render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );

    const row = container.querySelector('[data-testid="compare-row-V_cruise"]');
    expect(row).not.toBeNull();
    expect(row?.hasAttribute("data-differs")).toBe(false);
  });

  // -------------------------------------------------------------------------
  // 5. Loading state
  // -------------------------------------------------------------------------
  it("shows loading message when isLoading=true", () => {
    render(
      <VersionCompareView
        compareOut={null}
        isLoading={true}
        error={null}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/loading comparison/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 6. Error state
  // -------------------------------------------------------------------------
  it("shows error message when error is set", () => {
    render(
      <VersionCompareView
        compareOut={null}
        isLoading={false}
        error="Node 42 not found"
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByText(/node 42 not found/i)).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // 7. Close button calls onClose
  // -------------------------------------------------------------------------
  it("clicking the close button calls onClose", () => {
    const onClose = vi.fn();
    render(
      <VersionCompareView
        compareOut={null}
        isLoading={false}
        error={null}
        onClose={onClose}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /close compare panel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  // -------------------------------------------------------------------------
  // 8. Null metrics — no crash
  // -------------------------------------------------------------------------
  it("renders without crashing when metrics_a and metrics_b are null", () => {
    const compareOut = makeCompareOut(null, null);
    render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );
    // Should render headers but no metric rows
    expect(screen.getAllByText("Alpha build").length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // 9. SM differs is flagged
  // -------------------------------------------------------------------------
  it("marks SM row as differs when static margins differ significantly", () => {
    // A: CG at 0.088, NP at 0.115, MAC 0.25 → SM ≈ 10.8%
    // B: CG at 0.060, NP at 0.115, MAC 0.25 → SM ≈ 22%
    const ctxA = makeCtx({ cg_agg_m: 0.088, x_np_m: 0.115, mac_m: 0.25 });
    const ctxB = makeCtx({ cg_agg_m: 0.060, x_np_m: 0.115, mac_m: 0.25 });
    const compareOut = makeCompareOut(ctxA, ctxB);

    const { container } = render(
      <VersionCompareView
        compareOut={compareOut}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    );

    const row = container.querySelector('[data-testid="compare-row-SM"]');
    expect(row).not.toBeNull();
    expect(row?.getAttribute("data-differs")).toBe("true");
  });
});
