/**
 * Pure geometry utility for the GitKraken-style version graph (gh-961).
 *
 * `computeGraphLayout(tree)` turns a `TreeOut` lineage into a render-ready
 * `GraphLayout` consumed by `VersionGraph` / `GraphRow` components. No React,
 * no side effects, no network calls — pure functions only.
 *
 * Lane assignment algorithm (git-log style with lane compaction):
 *   1. main branch → lane 0.
 *   2. Each other branch gets the lowest available lane index > 0 at the
 *      moment its tip row is encountered (newest-first traversal). A lane is
 *      "available" if no other branch that is still "open" (tip not yet
 *      passed) occupies it.
 *   3. A branch's span runs from its tip row DOWN to the row of its fork
 *      parent (the node whose predecessor is on a different branch). Once the
 *      fork-parent row is processed, the lane is freed and can be reused.
 */

import type { TreeOut, TreeNodeOut, BranchOut } from "@/types/versioning";
import {
  LANE_COLORS,
  type GraphLayout,
  type GraphRow,
  type GraphRail,
  type GraphFork,
  type GraphPill,
  type DotStyle,
} from "@/types/versionGraph";

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

interface BranchMeta {
  branch: BranchOut;
  lane: number;
  color: string;
  /** Row index of this branch's tip (newest node). */
  tipRowIndex: number;
  /** Row index of the fork-parent row (the row where the branch diverges). */
  forkRowIndex: number;
  /**
   * Lane of the parent this branch forks INTO, set only for branches with a
   * real cross-lane fork (see `buildForkMap`). When non-null, the branch's
   * vertical rail stops one row above `forkRowIndex` — the fork curve, not a
   * vertical stub, bridges child → parent (otherwise it reads as a merge).
   */
  forkParentLane: number | null;
}

/** Pre-computed lookups shared across the layout helpers. */
interface LayoutContext {
  sorted: TreeNodeOut[];
  lastRowIndex: number;
  branchById: Map<number, BranchOut>;
  nodeRowIndex: Map<number, number>;
  nodeBranchId: Map<number, number | null>;
  branchTipRow: Map<number, number>;
  branchOldestNodePredId: Map<number, number | null>;
  mainBranch: BranchOut | null;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function computeGraphLayout(tree: TreeOut): GraphLayout {
  if (tree.nodes.length === 0) {
    return { rows: [], laneCount: 0 };
  }

  const ctx = buildContext(tree);
  const branchMetas = assignLanes(tree, ctx);
  const forkByRowIndex = buildForkMap(branchMetas, ctx);
  const nodeTipBranchId = buildTipMap(tree);

  const rows: GraphRow[] = ctx.sorted.map((n, rowIndex) =>
    buildRow(n, rowIndex, {
      ctx,
      branchMetas,
      forkByRowIndex,
      nodeTipBranchId,
    }),
  );

  return { rows, laneCount: computeLaneCount(branchMetas, ctx.sorted) };
}

// ---------------------------------------------------------------------------
// Context: sorting + lookup maps
// ---------------------------------------------------------------------------

function sortNodesNewestFirst(nodes: TreeNodeOut[]): TreeNodeOut[] {
  return [...nodes].sort((a, b) => {
    const tDiff = b.created_at.localeCompare(a.created_at);
    return tDiff !== 0 ? tDiff : b.id - a.id;
  });
}

function buildContext(tree: TreeOut): LayoutContext {
  const sorted = sortNodesNewestFirst(tree.nodes);
  const nodeRowIndex = new Map<number, number>(sorted.map((n, i) => [n.id, i]));

  const branchTipRow = new Map<number, number>();
  for (const b of tree.branches) {
    const idx = nodeRowIndex.get(b.head_id);
    if (idx !== undefined) branchTipRow.set(b.id, idx);
  }

  // For each branch, record the predecessor of its oldest (highest-row) node.
  const branchOldestNodeRow = new Map<number, number>();
  const branchOldestNodePredId = new Map<number, number | null>();
  for (const n of sorted) {
    if (n.branch_id === null) continue;
    const rowIdx = nodeRowIndex.get(n.id)!;
    const cur = branchOldestNodeRow.get(n.branch_id);
    if (cur === undefined || rowIdx > cur) {
      branchOldestNodeRow.set(n.branch_id, rowIdx);
      branchOldestNodePredId.set(n.branch_id, n.predecessor_id);
    }
  }

  // is_main is the SOLE authority for which branch is "main" — a branch may be
  // literally named "main" yet have been superseded by an adopted branch
  // (is_main=false). Never infer main-ness from the name.
  const mainBranch = tree.branches.find((b) => b.is_main) ?? null;

  return {
    sorted,
    lastRowIndex: sorted.length - 1,
    branchById: new Map(tree.branches.map((b) => [b.id, b])),
    nodeRowIndex,
    nodeBranchId: new Map(sorted.map((n) => [n.id, n.branch_id])),
    branchTipRow,
    branchOldestNodePredId,
    mainBranch,
  };
}

// ---------------------------------------------------------------------------
// Lane assignment
// ---------------------------------------------------------------------------

function getForkRowIndex(b: BranchOut, ctx: LayoutContext): number {
  const predId = ctx.branchOldestNodePredId.get(b.id);
  if (predId === null || predId === undefined) {
    return ctx.lastRowIndex; // branch starts at root — span ends at last row
  }
  const predBranchId = ctx.nodeBranchId.get(predId);
  if (predBranchId !== b.id) {
    return ctx.nodeRowIndex.get(predId) ?? ctx.lastRowIndex;
  }
  return ctx.lastRowIndex; // predecessor on same branch — no external fork
}

function isMainBranch(b: BranchOut): boolean {
  return b.is_main;
}

function makeBranchColor(): (b: BranchOut) => string {
  let paletteIdx = 0;
  return (b: BranchOut): string => {
    if (isMainBranch(b)) return LANE_COLORS.main;
    if (b.name.startsWith("ai/")) return LANE_COLORS.ai;
    return LANE_COLORS.palette[paletteIdx++ % LANE_COLORS.palette.length];
  };
}

/**
 * Greedy lowest-free-lane compaction. Main → lane 0; others get the lowest
 * free lane > 0 at the moment their tip row is encountered.
 */
function assignLanes(
  tree: TreeOut,
  ctx: LayoutContext,
): Map<number, BranchMeta> {
  const branchMetas = new Map<number, BranchMeta>();
  const occupiedLanes = new Set<number>();
  const branchColor = makeBranchColor();

  if (ctx.mainBranch) {
    branchMetas.set(ctx.mainBranch.id, {
      branch: ctx.mainBranch,
      lane: 0,
      color: LANE_COLORS.main,
      tipRowIndex: ctx.branchTipRow.get(ctx.mainBranch.id) ?? 0,
      forkRowIndex: ctx.lastRowIndex,
      forkParentLane: null,
    });
    occupiedLanes.add(0);
  }

  // Assign in tip-row order (earliest/newest tip first).
  const sortedBranches = [...tree.branches].sort(
    (a, b) =>
      (ctx.branchTipRow.get(a.id) ?? Infinity) -
      (ctx.branchTipRow.get(b.id) ?? Infinity),
  );

  for (const b of sortedBranches) {
    if (ctx.mainBranch && b.id === ctx.mainBranch.id) continue;

    const tipRow = ctx.branchTipRow.get(b.id) ?? 0;

    // Free lanes whose span ended with a gap before this tip row. Requiring
    // forkRowIndex + 1 < tipRow keeps adjacent spans on separate lanes
    // (git-log convention); only a clear gap allows reuse.
    for (const meta of branchMetas.values()) {
      if (meta.lane !== 0 && meta.forkRowIndex + 1 < tipRow) {
        occupiedLanes.delete(meta.lane);
      }
    }

    let lane = 1;
    while (occupiedLanes.has(lane)) lane++;

    branchMetas.set(b.id, {
      branch: b,
      lane,
      color: branchColor(b),
      tipRowIndex: tipRow,
      forkRowIndex: getForkRowIndex(b, ctx),
      forkParentLane: null, // set later in buildForkMap if a real fork exists
    });
    occupiedLanes.add(lane);
  }

  return branchMetas;
}

// ---------------------------------------------------------------------------
// Fork edges
// ---------------------------------------------------------------------------

/**
 * Map of parent-row index → fork edge. A fork is drawn on the row of a
 * branch's fork-parent (the predecessor of its oldest node, when on a
 * different branch). At most one fork per row.
 */
function buildForkMap(
  branchMetas: Map<number, BranchMeta>,
  ctx: LayoutContext,
): Map<number, GraphFork> {
  const forkByRowIndex = new Map<number, GraphFork>();

  for (const [bid, meta] of branchMetas) {
    if (ctx.mainBranch && bid === ctx.mainBranch.id) continue;

    const predId = ctx.branchOldestNodePredId.get(bid);
    if (predId === null || predId === undefined) continue;

    const predBranchId = ctx.nodeBranchId.get(predId);
    if (predBranchId === bid) continue; // same branch, no fork

    const forkRow = ctx.nodeRowIndex.get(predId);
    if (forkRow === undefined || forkByRowIndex.has(forkRow)) continue;

    const parentMeta =
      predBranchId != null ? branchMetas.get(predBranchId) : null;
    const parentLane = parentMeta ? parentMeta.lane : 0;

    // Mark this branch as having a real cross-lane fork so `buildRails` stops
    // its vertical rail one row above the fork row (the curve bridges instead).
    meta.forkParentLane = parentLane;

    forkByRowIndex.set(forkRow, {
      childLane: meta.lane,
      parentLane,
      color: meta.color,
    });
  }

  return forkByRowIndex;
}

// ---------------------------------------------------------------------------
// Per-row builders
// ---------------------------------------------------------------------------

function buildTipMap(tree: TreeOut): Map<number, number> {
  const nodeTipBranchId = new Map<number, number>();
  for (const b of tree.branches) {
    nodeTipBranchId.set(b.head_id, b.id);
  }
  return nodeTipBranchId;
}

function getNodeLane(
  n: TreeNodeOut,
  branchMetas: Map<number, BranchMeta>,
): { lane: number; color: string } {
  if (n.branch_id !== null) {
    const meta = branchMetas.get(n.branch_id);
    if (meta) return { lane: meta.lane, color: meta.color };
  }
  return { lane: 0, color: LANE_COLORS.legacy };
}

function buildPill(
  tipBranchId: number,
  ctx: LayoutContext,
  branchMetas: Map<number, BranchMeta>,
): GraphPill | null {
  const bMeta = branchMetas.get(tipBranchId);
  const bOut = ctx.branchById.get(tipBranchId);
  if (!bMeta || !bOut) return null;

  const isMain = isMainBranch(bOut);
  return {
    text: `${isMain ? "★" : "⎇"} ${bOut.name}`,
    isMain,
    color: bMeta.color,
  };
}

function buildRails(
  n: TreeNodeOut,
  rowIndex: number,
  ctx: LayoutContext,
  branchMetas: Map<number, BranchMeta>,
): GraphRail[] {
  const railMap = new Map<number, GraphRail>();

  for (const meta of branchMetas.values()) {
    const hasFork = meta.forkParentLane != null;
    // A forked child's vertical rail stops one row ABOVE the fork row; the
    // fork curve (not a vertical stub) bridges child → parent on the fork row.
    const railEnd = hasFork ? meta.forkRowIndex - 1 : meta.forkRowIndex;

    if (rowIndex >= meta.tipRowIndex && rowIndex <= railEnd) {
      railMap.set(meta.lane, {
        lane: meta.lane,
        color: meta.color,
        top: rowIndex > meta.tipRowIndex,
        // Forked branches always connect downward within their span: the last
        // rail row meets the curve below. No-fork branches use the plain span.
        bottom: hasFork ? true : rowIndex < meta.forkRowIndex,
      });
    }
  }

  // Legacy nodes: ensure a lane-0 rail exists, connecting to legacy neighbours.
  if (n.branch_id === null && !railMap.has(0)) {
    const newer = ctx.sorted[rowIndex - 1]; // row above = newer
    const older = ctx.sorted[rowIndex + 1]; // row below = older
    railMap.set(0, {
      lane: 0,
      color: LANE_COLORS.legacy,
      top: newer !== undefined && newer.branch_id === null,
      bottom: older !== undefined && older.branch_id === null,
    });
  }

  return [...railMap.values()].sort((a, b) => a.lane - b.lane);
}

interface RowDeps {
  ctx: LayoutContext;
  branchMetas: Map<number, BranchMeta>;
  forkByRowIndex: Map<number, GraphFork>;
  nodeTipBranchId: Map<number, number>;
}

function buildRow(
  n: TreeNodeOut,
  rowIndex: number,
  deps: RowDeps,
): GraphRow {
  const { ctx, branchMetas, forkByRowIndex, nodeTipBranchId } = deps;
  const { lane, color } = getNodeLane(n, branchMetas);

  const dotStyle: DotStyle = !n.is_immutable && n.is_head ? "hollow" : "filled";

  const tipBranchId = nodeTipBranchId.get(n.id);
  const isBranchTip = tipBranchId !== undefined;
  const pill =
    tipBranchId !== undefined
      ? buildPill(tipBranchId, ctx, branchMetas)
      : null;

  return {
    node: n,
    rowIndex,
    lane,
    color,
    dotStyle,
    isBranchTip,
    pill,
    rails: buildRails(n, rowIndex, ctx, branchMetas),
    fork: forkByRowIndex.get(rowIndex) ?? null,
  };
}

// ---------------------------------------------------------------------------
// Lane count
// ---------------------------------------------------------------------------

function computeLaneCount(
  branchMetas: Map<number, BranchMeta>,
  sorted: TreeNodeOut[],
): number {
  if (branchMetas.size > 0) {
    const maxLane = Math.max(...[...branchMetas.values()].map((m) => m.lane));
    return maxLane + 1;
  }
  // No branches: legacy nodes (if any) all share lane 0.
  return sorted.some((n) => n.branch_id === null) ? 1 : 0;
}
