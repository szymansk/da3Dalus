/**
 * gh-1050: Unit tests for the built-spar display + preview→confirm
 * "Add spar to wing" flow.
 *
 * Covers:
 *  - BuiltSparSection: front (main/index 0) / rear / reinforcement groups,
 *    joint labels, computed wall, infeasible banner.
 *  - AddSparToWingFlow: feasibility gating (button disabled when infeasible),
 *    dry-run preview (REPLACE warning + spar_index shown, front=0 highlighted),
 *    confirm → commit (onCommitted fired), error path.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import {
  BuiltSparSection,
  AddSparToWingFlow,
} from "@/components/workbench/SparSizingPanel";
import type {
  SparPlanResult,
  SparPieceOut,
  SparInsertResult,
} from "@/hooks/useSparPlan";

function piece(over: Partial<SparPieceOut> = {}): SparPieceOut {
  return {
    role: "front",
    spare_origin: [0, 0, 0],
    spare_vector: [0, 1, 0],
    outer_d: 0.0288,
    inner_d: 0.024,
    wall: 0.0024,
    shape: "tube",
    governing_y: 0,
    utilisation: 0.5,
    joint_to_next: null,
    feasible: true,
    infeasibility_reason: null,
    ...over,
  };
}

function feasiblePlan(): SparPlanResult {
  return {
    front_pieces: [
      piece({ joint_to_next: "telescoping" }),
      piece({ role: "front", joint_to_next: null }),
    ],
    rear_pieces: [piece({ role: "rear", outer_d: 0.012, inner_d: 0.008 })],
    front_joint: "continuous",
    rear_joint: "bent-pin",
    reinforcement: piece({ role: "front", outer_d: 0.03, inner_d: 0.0 }),
    feasible: true,
    infeasibility_reason: null,
  };
}

function previewResult(): SparInsertResult {
  return {
    dry_run: true,
    committed: false,
    wing_name: "Main Wing",
    planned_spares: [
      {
        segment_index: 0,
        spar_index: 0,
        role: "front",
        spare_support_dimension_width: 0.0288,
        spare_support_dimension_height: 0.0288,
        spare_length: 0.75,
        outer_d: 0.0288,
        inner_d: 0.024,
        spare_origin: [0, 0, 0],
        spare_vector: [0, 1, 0],
        joint_note: "telescoping",
        feasible: true,
      },
      {
        segment_index: 1,
        spar_index: 1,
        role: "rear",
        spare_support_dimension_width: 0.012,
        spare_support_dimension_height: 0.012,
        spare_length: 0.5,
        outer_d: 0.012,
        inner_d: 0.008,
        spare_origin: [0, 0, 0],
        spare_vector: [0, 1, 0],
        joint_note: null,
        feasible: true,
      },
    ],
    warnings: ["telescoping overlap modelled as butt joint"],
    feasible: true,
    infeasibility_reason: null,
  };
}

describe("BuiltSparSection (gh-1050)", () => {
  it("renders front (main, index 0), rear and reinforcement groups", () => {
    render(<BuiltSparSection plan={feasiblePlan()} />);
    const front = screen.getByTestId("built-spar-group-front");
    expect(front).toHaveTextContent(/main spar/i);
    expect(front).toHaveTextContent("0");
    expect(screen.getByTestId("built-spar-group-rear")).toHaveTextContent(/Rear/i);
    expect(
      screen.getByTestId("built-spar-group-reinforcement"),
    ).toHaveTextContent(/reinforcement/i);
  });

  it("shows OD × ID with computed wall and joint labels", () => {
    render(<BuiltSparSection plan={feasiblePlan()} />);
    const rows = screen.getAllByTestId("built-spar-piece");
    expect(rows[0]).toHaveTextContent("OD 28.8");
    expect(rows[0]).toHaveTextContent("ID 24.0");
    expect(rows[0]).toHaveTextContent("wall 2.4");
    expect(rows[0]).toHaveTextContent(/Telescoping/);
  });

  it("renders an infeasible banner when the plan is not buildable", () => {
    const plan = feasiblePlan();
    plan.feasible = false;
    plan.infeasibility_reason = "no tube fits at root";
    render(<BuiltSparSection plan={plan} />);
    expect(screen.getByTestId("built-spar-infeasible")).toHaveTextContent(
      "no tube fits at root",
    );
  });
});

describe("AddSparToWingFlow (gh-1050)", () => {
  it("disables the button when the plan is infeasible", () => {
    const plan = feasiblePlan();
    plan.feasible = false;
    const onInsert = vi.fn();
    render(<AddSparToWingFlow plan={plan} onInsert={onInsert} />);
    expect(screen.getByTestId("add-spar-to-wing-button")).toBeDisabled();
  });

  it("dry-run preview shows REPLACE warning, spar_index and front=0 highlighted", async () => {
    const onInsert = vi.fn().mockResolvedValue(previewResult());
    render(<AddSparToWingFlow plan={feasiblePlan()} onInsert={onInsert} />);

    fireEvent.click(screen.getByTestId("add-spar-to-wing-button"));

    await waitFor(() =>
      expect(screen.getByTestId("add-spar-preview-modal")).toBeInTheDocument(),
    );
    // first call is the dry-run preview
    expect(onInsert).toHaveBeenCalledWith(true);

    const warn = screen.getByTestId("add-spar-replace-warning");
    expect(warn).toHaveTextContent(
      "This replaces existing spars in segments 0, 1.",
    );

    const rows = screen.getAllByTestId("planned-spare-row");
    expect(rows).toHaveLength(2);
    // spar_index column shows 0 with the main marker
    expect(rows[0]).toHaveTextContent("0 (main)");
    expect(rows[1]).toHaveTextContent("1");
    // mapping warnings surfaced
    expect(screen.getByTestId("add-spar-warnings")).toHaveTextContent(
      "telescoping overlap",
    );
  });

  it("confirm calls commit (dry_run=false) and fires onCommitted", async () => {
    const onInsert = vi
      .fn()
      .mockResolvedValueOnce(previewResult())
      .mockResolvedValueOnce({ ...previewResult(), dry_run: false, committed: true });
    const onCommitted = vi.fn();
    render(
      <AddSparToWingFlow
        plan={feasiblePlan()}
        onInsert={onInsert}
        onCommitted={onCommitted}
      />,
    );

    fireEvent.click(screen.getByTestId("add-spar-to-wing-button"));
    await waitFor(() =>
      expect(screen.getByTestId("add-spar-confirm")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("add-spar-confirm"));

    await waitFor(() =>
      expect(screen.getByTestId("add-spar-success")).toBeInTheDocument(),
    );
    expect(onInsert).toHaveBeenNthCalledWith(1, true);
    expect(onInsert).toHaveBeenNthCalledWith(2, false);
    expect(onCommitted).toHaveBeenCalledTimes(1);
    // modal closed after commit
    expect(screen.queryByTestId("add-spar-preview-modal")).toBeNull();
  });

  it("surfaces a commit error inside the modal and keeps it open", async () => {
    const onInsert = vi
      .fn()
      .mockResolvedValueOnce(previewResult())
      .mockRejectedValueOnce(new Error("Spar insert failed (422): bad plan"));
    render(<AddSparToWingFlow plan={feasiblePlan()} onInsert={onInsert} />);

    fireEvent.click(screen.getByTestId("add-spar-to-wing-button"));
    await waitFor(() =>
      expect(screen.getByTestId("add-spar-confirm")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("add-spar-confirm"));

    await waitFor(() =>
      expect(screen.getByTestId("add-spar-preview-error")).toHaveTextContent(
        "bad plan",
      ),
    );
    expect(screen.getByTestId("add-spar-preview-modal")).toBeInTheDocument();
  });

  it("surfaces a preview (dry-run) error outside the modal", async () => {
    const onInsert = vi
      .fn()
      .mockRejectedValue(new Error("Spar insert failed: network down"));
    render(<AddSparToWingFlow plan={feasiblePlan()} onInsert={onInsert} />);

    fireEvent.click(screen.getByTestId("add-spar-to-wing-button"));
    await waitFor(() =>
      expect(screen.getByTestId("add-spar-error")).toHaveTextContent(
        "network down",
      ),
    );
    expect(screen.queryByTestId("add-spar-preview-modal")).toBeNull();
  });

  it("cancel closes the preview without committing", async () => {
    const onInsert = vi.fn().mockResolvedValue(previewResult());
    render(<AddSparToWingFlow plan={feasiblePlan()} onInsert={onInsert} />);
    fireEvent.click(screen.getByTestId("add-spar-to-wing-button"));
    await waitFor(() =>
      expect(screen.getByTestId("add-spar-cancel")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("add-spar-cancel"));
    expect(screen.queryByTestId("add-spar-preview-modal")).toBeNull();
    expect(onInsert).toHaveBeenCalledTimes(1); // only the preview
  });
});
