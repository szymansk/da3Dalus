/**
 * Shared contract for the GitKraken-style version graph layout (gh-961).
 *
 * `computeGraphLayout(tree)` (in `frontend/lib/versionGraphLayout.ts`) turns a
 * `TreeOut` lineage into a pure, render-ready geometry description. The React
 * components (`VersionGraph`, `GraphRow`) consume this and draw SVG rails/dots
 * without re-deriving any topology.
 *
 * Coordinate model (per row):
 *   - Lanes are integer columns 0..laneCount-1. Lane 0 is `main`.
 *   - A row has a fixed height; the node dot sits at the vertical centre of its
 *     lane. Components map `lane` → x via `LANE_X0 + lane * LANE_GAP`.
 *   - `rails` are the vertical branch lines passing through THIS row (a lane may
 *     have a rail even if no node of that lane sits in this row — the line just
 *     passes through).
 *   - `fork` is set on the row where a child branch's earliest node connects
 *     back to its parent node on another lane (the diverging curve).
 */

import type { TreeNodeOut } from "@/types/versioning";

/** Snapshot (immutable) → filled dot; editable head → hollow ring. */
export type DotStyle = "filled" | "hollow";

/** A vertical branch line passing through a single row, in one lane. */
export interface GraphRail {
  lane: number;
  color: string;
  /** Rail continues into the row above (connects upward). */
  top: boolean;
  /** Rail continues into the row below (connects downward). */
  bottom: boolean;
}

/**
 * A diverging curve drawn on the parent's row: from the child lane (coming down
 * from above) into the parent node on `parentLane`. Coloured with the child
 * branch colour, matching GitKraken.
 */
export interface GraphFork {
  childLane: number;
  parentLane: number;
  color: string;
}

/** Branch-tip label pill (only present on a branch's newest/tip node). */
export interface GraphPill {
  text: string;
  isMain: boolean;
  color: string;
}

/** One fully-resolved row, newest first. */
export interface GraphRow {
  node: TreeNodeOut;
  rowIndex: number;
  /** Lane the node's dot sits in. */
  lane: number;
  /** Lane colour (also the dot colour). */
  color: string;
  dotStyle: DotStyle;
  /** True when this node is the head/tip of its branch (carries the pill). */
  isBranchTip: boolean;
  /** Branch pill, only on tips; null otherwise. */
  pill: GraphPill | null;
  /** Every vertical rail crossing this row (includes the node's own lane). */
  rails: GraphRail[];
  /** Diverging curve into a parent on another lane, or null. */
  fork: GraphFork | null;
}

export interface GraphLayout {
  rows: GraphRow[];
  laneCount: number;
}

/**
 * Deterministic lane colours.
 *   - main          → primary orange
 *   - ai/* branches → violet
 *   - other human   → rotating palette by assignment order
 *   - legacy (branch_id null) → neutral grey
 */
export const LANE_COLORS = {
  main: "#FF8400",
  ai: "#a78bfa",
  legacy: "#6b7280",
  palette: ["#2dd4bf", "#3b82f6", "#f59e0b", "#ec4899", "#22c55e", "#eab308"],
} as const;

/*
 * ---------------------------------------------------------------------------
 * WORKED EXAMPLE (the spec mockup) — used to align implementations + tests.
 * ---------------------------------------------------------------------------
 * Input nodes (created_at desc), branches: main(lane0, is_main),
 * ai/winglet-exp(forked from v1.1), fix/stall(forked from v1.0):
 *
 *   row0  working head   branch=main  pred=v1.1   is_head  editable   → lane0, hollow, tip(★ main), rails[{0,top:false,bottom:true}]
 *   row1  winglet draft  branch=ai    pred=v1.1   is_head  editable   → lane1, hollow, tip(⎇ ai/winglet-exp),
 *                                                                         rails[{0,top,bottom},{1,top:false,bottom:true}]
 *   row2  v1.1           branch=main  pred=v1.0   snapshot            → lane0, filled,
 *                                                                         rails[{0,top,bottom}], fork{childLane:1,parentLane:0}
 *   row3  washout +1.5   branch=fix   pred=v1.0   is_head  editable   → lane2, hollow, tip(⎇ fix/stall),
 *                                                                         rails[{0,top,bottom},{2,top:false,bottom:true}]
 *   row4  v1.0           branch=main  pred=root   snapshot            → lane0, filled,
 *                                                                         rails[{0,top,bottom}], fork{childLane:2,parentLane:0}
 *   row5  root           branch=main  pred=null   snapshot            → lane0, filled,
 *                                                                         rails[{0,top,bottom:false}]
 *
 * laneCount = 3. Lane 1 (ai) is occupied rows[1..2]; lane 2 (fix) rows[3..4];
 * once a branch's span ends its lane index may be reused by a later branch.
 */
