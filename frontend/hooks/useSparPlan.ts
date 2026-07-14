// frontend/hooks/useSparPlan.ts
// gh-1050: Buildable spar plan + preview→commit insert into the wing.
//
// Two manual fetch-based POSTs (mirroring useSparSizing):
//   - run()    → POST /aeroplanes/{id}/spar-plan          (buildable pieces)
//   - insert() → POST /aeroplanes/{id}/spar-plan/insert   (dry_run preview / commit)
//
// All dimensions in the responses are in METRES (project convention).

"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";
import { parseApiError } from "@/lib/parseApiError";

// ---- Request types (mirror app/schemas/spar_plan.py + spar_insert.py) -------

export interface MomentSample {
  y_span: number; // 0..1 across the semi-span (root=0, tip=1)
  bending_moment_Nm: number;
}

export interface SparPlanParams {
  material_id: number;
  moments: MomentSample[];
  wing_name?: string | null;
  front_x_over_chord?: number | null;
  rear_x_over_chord?: number;
  n_span?: number;
  packing_factor?: number;
  safety_factor_j?: number;
  sigma_allow_mpa_override?: number | null;
  // gh-1080: cross-section shape for both spars (mirrors SparPlanRequest.shape).
  // Default 'tube' when omitted (backend default). Choosing 'rod' drives the
  // solver to produce solid pieces (inner_d=0, joiner joints, stock snap).
  shape?: "tube" | "rod" | "rectangular" | "capped";
}

// ---- Response types: spar-plan (buildable pieces, metres) -------------------

export interface SparPieceOut {
  role: string; // "front" | "rear"
  spare_origin: number[];
  spare_vector: number[];
  outer_d: number; // m
  inner_d: number; // m
  wall: number; // m
  shape: string;
  governing_y: number; // m
  // gh-1072: chordwise location (x/c, 0..1) this piece was placed at. Front
  // (main) ≈ section max-thickness; rear (torsion) = clamped rear x/c.
  x_over_chord: number;
  // gh-1057/gh-1060: spanwise extent of this piece (metres, root=0). For a
  // telescoping run the NEXT piece's y_start is the telescoping joint position.
  y_start: number; // m
  y_end: number; // m
  utilisation: number;
  joint_to_next: string | null;
  feasible: boolean;
  infeasibility_reason: string | null;
  // gh-1080: extended dims for rectangular/capped (metres); null/absent for tube/rod.
  width?: number | null; // m — web/flange width for rectangular
  height?: number | null; // m — profile height for rectangular (= band depth)
  cap_width?: number | null; // m — flange width for capped (I/C-beam)
}

export interface SparPlanResult {
  front_pieces: SparPieceOut[];
  rear_pieces: SparPieceOut[];
  front_joint: string;
  rear_joint: string;
  reinforcement: SparPieceOut | null;
  feasible: boolean;
  infeasibility_reason: string | null;
}

// ---- Response types: insert (planned spares, metres) -----------------------

export interface PlannedSpareOut {
  segment_index: number;
  spar_index: number;
  role: string;
  spare_support_dimension_width: number; // m (= outer_d)
  spare_support_dimension_height: number; // m (= outer_d)
  spare_length: number; // m
  outer_d: number; // m
  inner_d: number; // m
  spare_origin: number[];
  spare_vector: number[];
  joint_note: string | null;
  feasible: boolean;
}

export interface SparInsertResult {
  dry_run: boolean;
  committed: boolean;
  wing_name: string;
  planned_spares: PlannedSpareOut[];
  warnings: string[];
  feasible: boolean;
  infeasibility_reason: string | null;
  // gh-1058: PK of the auto-snapshot taken BEFORE the destructive commit so the
  // user can one-click revert. Null on a dry-run (nothing was mutated).
  snapshot_id: number | null;
  // gh-1063: when the main (front) spar telescopes the host segment is SPLIT at
  // each joint; these are the resulting per-sub-segment spanwise lengths (m),
  // root→tip. Null/single-element when no split happens.
  planned_segment_lengths: number[] | null;
}

// ---- Body builder (shared by run + insert) ---------------------------------

function buildPlanBody(params: SparPlanParams): Record<string, unknown> {
  const body: Record<string, unknown> = {
    material_id: params.material_id,
    moments: params.moments,
  };
  if (params.wing_name != null) body.wing_name = params.wing_name;
  if (params.front_x_over_chord != null)
    body.front_x_over_chord = params.front_x_over_chord;
  if (params.rear_x_over_chord != null)
    body.rear_x_over_chord = params.rear_x_over_chord;
  if (params.n_span != null) body.n_span = params.n_span;
  if (params.packing_factor != null) body.packing_factor = params.packing_factor;
  if (params.safety_factor_j != null)
    body.safety_factor_j = params.safety_factor_j;
  if (params.sigma_allow_mpa_override != null)
    body.sigma_allow_mpa_override = params.sigma_allow_mpa_override;
  // gh-1080: send shape when explicitly set; omitting lets the backend default
  // to 'tube', which keeps the wire protocol backwards-compatible.
  if (params.shape != null) body.shape = params.shape;
  return body;
}

// ---- Hook ------------------------------------------------------------------

export function useSparPlan(aeroplaneId: string | null) {
  const [plan, setPlan] = useState<SparPlanResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (params: SparPlanParams) => {
      if (!aeroplaneId) return;
      setIsRunning(true);
      setError(null);
      setPlan(null);

      try {
        const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/spar-plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildPlanBody(params)),
        });
        if (!res.ok) {
          throw new Error(await parseApiError(res, "Spar plan"));
        }
        const data: SparPlanResult = await res.json();
        setPlan(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsRunning(false);
      }
    },
    [aeroplaneId],
  );

  // insert: dry_run=true → preview (no writes); dry_run=false → persist.
  // Returns the result (or null on error). Errors are also surfaced on the
  // returned promise so the caller can branch on success.
  const insert = useCallback(
    async (
      params: SparPlanParams,
      dryRun: boolean,
    ): Promise<SparInsertResult> => {
      if (!aeroplaneId) {
        throw new Error("No aeroplane selected");
      }
      const body = { ...buildPlanBody(params), dry_run: dryRun };
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/spar-plan/insert`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!res.ok) {
        throw new Error(await parseApiError(res, "Spar insert"));
      }
      return (await res.json()) as SparInsertResult;
    },
    [aeroplaneId],
  );

  // gh-1060: revert a destructive insert-commit by restoring its pre-insert
  // snapshot. POST /aeroplanes/{snapshot_id}/restore forks an editable head
  // from the immutable snapshot (BranchRequest body: name + created_by).
  // Throws readably on a non-ok response so the caller can surface the error.
  const restoreSnapshot = useCallback(
    async (snapshotId: number): Promise<void> => {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${snapshotId}/restore`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Revert spar insert",
            created_by: "human",
          }),
        },
      );
      if (!res.ok) {
        throw new Error(await parseApiError(res, "Snapshot restore"));
      }
    },
    [],
  );

  return { plan, isRunning, error, run, insert, restoreSnapshot };
}
