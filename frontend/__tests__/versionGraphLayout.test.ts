/**
 * Unit tests for frontend/lib/versionGraphLayout.ts (gh-961).
 *
 * Covers:
 * - newest-first ordering with stable tiebreak
 * - main always lane 0, continuous rail top→bottom
 * - forked branch: correct lane, tip pill, hollow dot, rail span, fork edge
 * - lane reuse after a branch span ends
 * - snapshot=filled vs head=hollow
 * - single-node lineage and empty tree (no crash)
 * - legacy nodes (branch_id null)
 *
 * The fixtures match the WORKED EXAMPLE from frontend/types/versionGraph.ts.
 */

import { describe, it, expect } from "vitest";
import { computeGraphLayout } from "@/lib/versionGraphLayout";
import type { TreeOut, TreeNodeOut, BranchOut } from "@/types/versioning";
import { LANE_COLORS } from "@/types/versionGraph";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function node(
  id: number,
  branch_id: number | null,
  predecessor_id: number | null,
  created_at: string,
  overrides: Partial<TreeNodeOut> = {},
): TreeNodeOut {
  return {
    id,
    uuid: `uuid-${id}`,
    name: `node-${id}`,
    branch_id,
    predecessor_id,
    root_id: 1,
    is_immutable: false,
    is_head: false,
    version_label: null,
    version_note: null,
    created_by: null,
    created_at,
    ...overrides,
  };
}

function branch(
  id: number,
  name: string,
  head_id: number,
  is_main = false,
  root_id = 1,
): BranchOut {
  return {
    id,
    root_id,
    head_id,
    name,
    is_main,
    created_by: null,
    created_at: "2026-01-01T00:00:00Z",
  };
}

// ---------------------------------------------------------------------------
// WORKED EXAMPLE fixture
// ---------------------------------------------------------------------------
//
//  main branch  (b1, is_main, lane 0):  root(1) → v1.0(2) → v1.1(3) → working(4)
//  ai branch    (b2, "ai/winglet-exp"): v1.1(3) → winglet(5)   [forked from node 3]
//  fix branch   (b3, "fix/stall"):      v1.0(2) → washout(6)   [forked from node 2]
//
//  Created-at ordering newest→oldest: working(4), winglet(5), v1.1(3), washout(6), v1.0(2), root(1)
//  But our sort is by created_at DESC — we supply explicit timestamps.
//
//  node ids and their timestamps (newest first):
//    4  working    2026-06-10T12:00:00Z   main  pred=3  is_head,!immutable
//    5  winglet    2026-06-09T12:00:00Z   ai    pred=3  is_head,!immutable
//    3  v1.1       2026-06-08T12:00:00Z   main  pred=2  immutable
//    6  washout    2026-06-07T12:00:00Z   fix   pred=2  is_head,!immutable
//    2  v1.0       2026-06-06T12:00:00Z   main  pred=1  immutable
//    1  root       2026-06-05T12:00:00Z   main  pred=null immutable
//
//  Expected rows (index 0 = newest):
//    row0 node4  lane0  hollow  tip(★ main)
//    row1 node5  lane1  hollow  tip(⎇ ai/winglet-exp)  rails[0,1]
//    row2 node3  lane0  filled  no pill  rails[0,1]  fork{childLane:1,parentLane:0}
//    row3 node6  lane2  hollow  tip(⎇ fix/stall)  rails[0,2]
//    row4 node2  lane0  filled  no pill  rails[0,2]  fork{childLane:2,parentLane:0}
//    row5 node1  lane0  filled  no pill  rails[0]

const NODES_WORKED: TreeNodeOut[] = [
  node(4, 1, 3, "2026-06-10T12:00:00Z", { is_head: true, is_immutable: false }),
  node(5, 2, 3, "2026-06-09T12:00:00Z", { is_head: true, is_immutable: false }),
  node(3, 1, 2, "2026-06-08T12:00:00Z", { is_immutable: true }),
  node(6, 3, 2, "2026-06-07T12:00:00Z", { is_head: true, is_immutable: false }),
  node(2, 1, 1, "2026-06-06T12:00:00Z", { is_immutable: true }),
  node(1, 1, null, "2026-06-05T12:00:00Z", { is_immutable: true }),
];

const BRANCHES_WORKED: BranchOut[] = [
  branch(1, "main", 4, true),
  branch(2, "ai/winglet-exp", 5, false),
  branch(3, "fix/stall", 6, false),
];

const TREE_WORKED: TreeOut = {
  root_id: 1,
  nodes: NODES_WORKED,
  branches: BRANCHES_WORKED,
};

// ---------------------------------------------------------------------------
// 1. Ordering: newest first, stable tiebreak by id desc
// ---------------------------------------------------------------------------

describe("ordering", () => {
  it("sorts rows newest-first by created_at", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const timestamps = layout.rows.map((r) => r.node.created_at);
    for (let i = 1; i < timestamps.length; i++) {
      expect(timestamps[i] <= timestamps[i - 1]).toBe(true);
    }
  });

  it("stable tiebreak by id descending when timestamps are equal", () => {
    const treeWithTie: TreeOut = {
      root_id: 1,
      nodes: [
        node(3, 1, 2, "2026-01-01T00:00:00Z", { is_head: true }),
        node(1, 1, null, "2026-01-01T00:00:00Z", { is_immutable: true }),
        node(2, 1, 1, "2026-01-01T00:00:00Z", { is_immutable: true }),
      ],
      branches: [branch(1, "main", 3, true)],
    };
    const layout = computeGraphLayout(treeWithTie);
    expect(layout.rows[0].node.id).toBe(3);
    expect(layout.rows[1].node.id).toBe(2);
    expect(layout.rows[2].node.id).toBe(1);
  });

  it("assigns correct rowIndex (0-based, same as array position)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    layout.rows.forEach((r, i) => {
      expect(r.rowIndex).toBe(i);
    });
  });
});

// ---------------------------------------------------------------------------
// 2. Main branch: lane 0
// ---------------------------------------------------------------------------

describe("main branch lane", () => {
  it("all main-branch nodes are in lane 0", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const mainNodes = [1, 2, 3, 4];
    for (const id of mainNodes) {
      const row = layout.rows.find((r) => r.node.id === id)!;
      expect(row.lane).toBe(0);
    }
  });

  it("main branch color is LANE_COLORS.main (#FF8400)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 4)!;
    expect(row.color).toBe(LANE_COLORS.main);
  });

  it("main lane has rail in every row (top and/or bottom)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    for (const row of layout.rows) {
      const mainRail = row.rails.find((r) => r.lane === 0);
      expect(mainRail).toBeDefined();
    }
  });

  it("root node rail: top=true (successor above it in display), bottom=false (nothing below oldest)", () => {
    // Rows are newest-first. Root is the last row (highest rowIndex).
    // top=true means the rail continues into the row above (= newer = smaller rowIndex).
    // bottom=false means nothing below (= older = no further rows).
    const layout = computeGraphLayout(TREE_WORKED);
    const rootRow = layout.rows.find((r) => r.node.id === 1)!;
    const rail = rootRow.rails.find((r) => r.lane === 0)!;
    expect(rail.top).toBe(true);
    expect(rail.bottom).toBe(false);
  });

  it("newest head node rail: top=false (nothing newer above), bottom=true (predecessor below)", () => {
    // Head is at row0. top=false (no row above). bottom=true (v1.1 is below it).
    const layout = computeGraphLayout(TREE_WORKED);
    const headRow = layout.rows.find((r) => r.node.id === 4)!;
    const rail = headRow.rails.find((r) => r.lane === 0)!;
    expect(rail.top).toBe(false);
    expect(rail.bottom).toBe(true);
  });

  it("interior main node rail: top=true, bottom=true", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const v11 = layout.rows.find((r) => r.node.id === 3)!; // v1.1
    const rail = v11.rails.find((r) => r.lane === 0)!;
    expect(rail.top).toBe(true);
    expect(rail.bottom).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 3. Forked ai branch
// ---------------------------------------------------------------------------

describe("ai branch fork", () => {
  it("ai/winglet-exp node is in lane 1", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 5)!;
    expect(row.lane).toBe(1);
  });

  it("ai branch color is LANE_COLORS.ai (#a78bfa)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 5)!;
    expect(row.color).toBe(LANE_COLORS.ai);
  });

  it("ai tip has isBranchTip=true and pill with ⎇ prefix", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 5)!;
    expect(row.isBranchTip).toBe(true);
    expect(row.pill).not.toBeNull();
    expect(row.pill!.text).toBe("⎇ ai/winglet-exp");
    expect(row.pill!.isMain).toBe(false);
    expect(row.pill!.color).toBe(LANE_COLORS.ai);
  });

  it("ai tip node is hollow (editable head)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 5)!;
    expect(row.dotStyle).toBe("hollow");
  });

  it("ai rail present at tip row (top=false, bottom=true)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const tipRow = layout.rows.find((r) => r.node.id === 5)!;
    const rail = tipRow.rails.find((r) => r.lane === 1)!;
    expect(rail).toBeDefined();
    expect(rail.top).toBe(false);
    // The child tip rail connects DOWN to the fork curve (one row below).
    expect(rail.bottom).toBe(true);
  });

  it("ai lane rail is ABSENT on the fork (v1.1) row — only the curve bridges", () => {
    // The child lane rail stops one row above the fork row. On the fork row
    // itself only the bézier curve connects child → parent; a vertical child
    // stub there would read as a merge.
    const layout = computeGraphLayout(TREE_WORKED);
    const parentRow = layout.rows.find((r) => r.node.id === 3)!; // v1.1
    const childRail = parentRow.rails.find((r) => r.lane === 1);
    expect(childRail).toBeUndefined();
  });

  it("fork row contains ONLY the main lane rail (lane 0) plus the fork curve", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const parentRow = layout.rows.find((r) => r.node.id === 3)!; // v1.1
    expect(parentRow.rails.map((r) => r.lane)).toEqual([0]);
    expect(parentRow.fork).not.toBeNull();
  });

  it("fork is set on the parent (v1.1) row with correct childLane/parentLane", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const parentRow = layout.rows.find((r) => r.node.id === 3)!;
    expect(parentRow.fork).not.toBeNull();
    expect(parentRow.fork!.childLane).toBe(1);
    expect(parentRow.fork!.parentLane).toBe(0);
    expect(parentRow.fork!.color).toBe(LANE_COLORS.ai);
  });

  it("fork is NOT set on the ai tip row itself", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const tipRow = layout.rows.find((r) => r.node.id === 5)!;
    expect(tipRow.fork).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 4. fix/stall branch
// ---------------------------------------------------------------------------

describe("fix branch", () => {
  it("fix/stall node is in lane 2", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 6)!;
    expect(row.lane).toBe(2);
  });

  it("fix branch color is from the palette (first palette color)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 6)!;
    expect(row.color).toBe(LANE_COLORS.palette[0]);
  });

  it("fork on v1.0 (node 2) row for fix/stall branch", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const parentRow = layout.rows.find((r) => r.node.id === 2)!;
    expect(parentRow.fork).not.toBeNull();
    expect(parentRow.fork!.childLane).toBe(2);
    expect(parentRow.fork!.parentLane).toBe(0);
    expect(parentRow.fork!.color).toBe(LANE_COLORS.palette[0]);
  });

  it("fix fork row (v1.0) has ONLY the main lane rail — no lane-2 child stub", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const parentRow = layout.rows.find((r) => r.node.id === 2)!; // v1.0
    expect(parentRow.rails.map((r) => r.lane)).toEqual([0]);
  });

  it("fix tip row (washout) rail connects DOWN to the fork curve (bottom=true)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const tipRow = layout.rows.find((r) => r.node.id === 6)!; // washout
    const rail = tipRow.rails.find((r) => r.lane === 2)!;
    expect(rail).toBeDefined();
    expect(rail.bottom).toBe(true);
  });

  it("fix tip pill text is ⎇ fix/stall", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 6)!;
    expect(row.pill!.text).toBe("⎇ fix/stall");
  });
});

// ---------------------------------------------------------------------------
// 4b. Fork connector reads as branch-off, not merge
// ---------------------------------------------------------------------------

describe("fork renders as branch-off (not merge)", () => {
  it("on every fork row, the child lane has NO rail but the fork is set", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    for (const row of layout.rows) {
      if (row.fork === null) continue;
      const childLane = row.fork.childLane;
      const childRail = row.rails.find((r) => r.lane === childLane);
      // No vertical child stub on the fork row — only the curve bridges.
      expect(childRail).toBeUndefined();
      expect(row.fork).not.toBeNull();
    }
  });

  it("each forked branch's tip rail connects downward to its curve (bottom=true)", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    // ai tip (node 5, lane 1) and fix tip (node 6, lane 2) both fork from main.
    for (const [nodeId, lane] of [
      [5, 1],
      [6, 2],
    ] as const) {
      const tipRow = layout.rows.find((r) => r.node.id === nodeId)!;
      const rail = tipRow.rails.find((r) => r.lane === lane)!;
      expect(rail).toBeDefined();
      expect(rail.bottom).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// 4c. Two branches forking from the SAME parent row
// ---------------------------------------------------------------------------
//
//  Both branchA and branchB diverge from the SAME main node (node 2).
//  Their fork rows coincide. Only ONE curve slot is drawn on the shared fork
//  row (first-come), but BOTH child lanes must still terminate their vertical
//  rail one row above the fork row — otherwise the second branch reintroduces
//  the merge-look bug (vertical stub + no curve).
//
//  Timeline (newest first):
//    node3  main     pred=2   2026-06-10  (main head)        row0
//    node4  branchA  pred=2   2026-06-09  (branchA tip)      row1
//    node5  branchB  pred=2   2026-06-08  (branchB tip)      row2
//    node2  main     pred=1   2026-06-07  (SHARED fork row)  row3
//    node1  main     pred=null 2026-06-06 (root)             row4
//
//  branchA: tipRow=1, forkRow=3 → lane 1, rail rows[1..2]
//  branchB: tipRow=2, forkRow=3 → lane 2, rail rows[2..2]
//  On row3 (shared fork): neither lane 1 nor lane 2 has a rail; exactly one fork.

const SAME_PARENT_NODES: TreeNodeOut[] = [
  node(3, 1, 2, "2026-06-10T00:00:00Z", { is_head: true }),
  node(4, 2, 2, "2026-06-09T00:00:00Z", { is_head: true }),
  node(5, 3, 2, "2026-06-08T00:00:00Z", { is_head: true }),
  node(2, 1, 1, "2026-06-07T00:00:00Z", { is_immutable: true }),
  node(1, 1, null, "2026-06-06T00:00:00Z", { is_immutable: true }),
];

const SAME_PARENT_BRANCHES: BranchOut[] = [
  branch(1, "main", 3, true),
  branch(2, "feat/branch-A", 4, false),
  branch(3, "fix/branch-B", 5, false),
];

const TREE_SAME_PARENT: TreeOut = {
  root_id: 1,
  nodes: SAME_PARENT_NODES,
  branches: SAME_PARENT_BRANCHES,
};

describe("two branches from the same parent row", () => {
  it("on the shared fork row, NEITHER child lane has a vertical rail", () => {
    const layout = computeGraphLayout(TREE_SAME_PARENT);
    const forkRow = layout.rows.find((r) => r.node.id === 2)!; // shared parent
    // Only the main backbone lane should remain on the fork row.
    expect(forkRow.rails.map((r) => r.lane)).toEqual([0]);
  });

  it("exactly one fork is set on the shared fork row", () => {
    const layout = computeGraphLayout(TREE_SAME_PARENT);
    const forkRow = layout.rows.find((r) => r.node.id === 2)!;
    expect(forkRow.fork).not.toBeNull();
    expect(forkRow.fork!.parentLane).toBe(0);
  });

  it("no OTHER row carries a duplicate fork for these branches", () => {
    const layout = computeGraphLayout(TREE_SAME_PARENT);
    const rowsWithFork = layout.rows.filter((r) => r.fork !== null);
    expect(rowsWithFork).toHaveLength(1);
    expect(rowsWithFork[0].node.id).toBe(2);
  });

  it("BOTH child tip rails connect downward to the curve (bottom=true)", () => {
    const layout = computeGraphLayout(TREE_SAME_PARENT);
    const tipA = layout.rows.find((r) => r.node.id === 4)!; // lane 1
    const tipB = layout.rows.find((r) => r.node.id === 5)!; // lane 2
    const railA = tipA.rails.find((r) => r.lane === 1)!;
    const railB = tipB.rails.find((r) => r.lane === 2)!;
    expect(railA).toBeDefined();
    expect(railA.bottom).toBe(true);
    expect(railB).toBeDefined();
    expect(railB.bottom).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 5. Dot style
// ---------------------------------------------------------------------------

describe("dotStyle", () => {
  it("immutable snapshot nodes are filled", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const immutableIds = [1, 2, 3]; // root, v1.0, v1.1
    for (const id of immutableIds) {
      const row = layout.rows.find((r) => r.node.id === id)!;
      expect(row.dotStyle).toBe("filled");
    }
  });

  it("editable head nodes are hollow", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const headIds = [4, 5, 6]; // working, winglet, washout
    for (const id of headIds) {
      const row = layout.rows.find((r) => r.node.id === id)!;
      expect(row.dotStyle).toBe("hollow");
    }
  });

  it("editable non-head node defaults to filled", () => {
    const tree: TreeOut = {
      root_id: 10,
      nodes: [
        node(12, 1, 11, "2026-06-10T00:00:00Z", { is_head: true, is_immutable: false }),
        node(11, 1, 10, "2026-06-09T00:00:00Z", { is_head: false, is_immutable: false }),
        node(10, 1, null, "2026-06-08T00:00:00Z", { is_immutable: true }),
      ],
      branches: [branch(1, "main", 12, true, 10)],
    };
    const layout = computeGraphLayout(tree);
    const midRow = layout.rows.find((r) => r.node.id === 11)!;
    expect(midRow.dotStyle).toBe("filled");
  });
});

// ---------------------------------------------------------------------------
// 6. laneCount
// ---------------------------------------------------------------------------

describe("laneCount", () => {
  it("is 3 for the worked example", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    expect(layout.laneCount).toBe(3);
  });

  it("is 1 for a single-branch tree", () => {
    const tree: TreeOut = {
      root_id: 1,
      nodes: [
        node(2, 1, 1, "2026-06-06T00:00:00Z", { is_head: true }),
        node(1, 1, null, "2026-06-05T00:00:00Z", { is_immutable: true }),
      ],
      branches: [branch(1, "main", 2, true)],
    };
    const layout = computeGraphLayout(tree);
    expect(layout.laneCount).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// 7. Lane reuse
// ---------------------------------------------------------------------------

describe("lane reuse", () => {
  // Lane reuse happens when branch-B's tip starts AFTER a gap following branch-A's
  // fork row (i.e. forkRowA + 1 < tipRowB — they are not adjacent spans).
  //
  // Timeline (newest first):
  //   node6  main  pred=5   2026-06-12  (main head)    row0
  //   node5  main  pred=3   2026-06-11  (main mid)     row1
  //   node4  branchA pred=3 2026-06-10  (branchA tip)  row2
  //   node3  main  pred=2   2026-06-09  (fork parent A) row3
  //   node2  main  pred=1   2026-06-08  (main mid)     row4
  //   node7  branchB pred=1 2026-06-07  (branchB tip)  row5
  //   node1  main  pred=null 2026-06-06  (root, fork parent B)  row6
  //
  // branchA span: rows[2..3]  → lane 1
  // branchB span: rows[5..6]  → lane 1 REUSED (gap: row4 is between forkA=3 and tipB=5)

  const REUSE_NODES: TreeNodeOut[] = [
    node(6, 1, 5, "2026-06-12T00:00:00Z", { is_head: true }),
    node(5, 1, 3, "2026-06-11T00:00:00Z", { is_immutable: true }),
    node(4, 2, 3, "2026-06-10T00:00:00Z", { is_head: true }),
    node(3, 1, 2, "2026-06-09T00:00:00Z", { is_immutable: true }),
    node(2, 1, 1, "2026-06-08T00:00:00Z", { is_immutable: true }),
    node(7, 3, 1, "2026-06-07T00:00:00Z", { is_head: true }),
    node(1, 1, null, "2026-06-06T00:00:00Z", { is_immutable: true }),
  ];

  const REUSE_BRANCHES: BranchOut[] = [
    branch(1, "main", 6, true),
    branch(2, "feat/branch-A", 4, false),
    branch(3, "fix/branch-B", 7, false),
  ];

  const TREE_REUSE: TreeOut = {
    root_id: 1,
    nodes: REUSE_NODES,
    branches: REUSE_BRANCHES,
  };

  it("second branch reuses lane 1 when there is a gap after first branch span", () => {
    const layout = computeGraphLayout(TREE_REUSE);
    const rowA = layout.rows.find((r) => r.node.id === 4)!; // branchA tip → lane 1
    const rowB = layout.rows.find((r) => r.node.id === 7)!; // branchB tip → should reuse lane 1
    expect(rowA.lane).toBe(1);
    expect(rowB.lane).toBe(1);
  });

  it("laneCount stays 2 when lane is reused", () => {
    const layout = computeGraphLayout(TREE_REUSE);
    expect(layout.laneCount).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// 8. Single-node tree (only root) — no crash
// ---------------------------------------------------------------------------

describe("single-node tree", () => {
  const TREE_SINGLE: TreeOut = {
    root_id: 42,
    nodes: [
      node(42, 1, null, "2026-01-01T00:00:00Z", { is_immutable: true }),
    ],
    branches: [branch(1, "main", 42, true, 42)],
  };

  it("returns one row without crashing", () => {
    const layout = computeGraphLayout(TREE_SINGLE);
    expect(layout.rows).toHaveLength(1);
  });

  it("laneCount is 1", () => {
    expect(computeGraphLayout(TREE_SINGLE).laneCount).toBe(1);
  });

  it("single node rail: top=false, bottom=false", () => {
    const layout = computeGraphLayout(TREE_SINGLE);
    const rail = layout.rows[0].rails.find((r) => r.lane === 0)!;
    expect(rail.top).toBe(false);
    expect(rail.bottom).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 9. Empty tree — no crash
// ---------------------------------------------------------------------------

describe("empty tree", () => {
  const TREE_EMPTY: TreeOut = {
    root_id: 0,
    nodes: [],
    branches: [],
  };

  it("returns empty rows without crashing", () => {
    const layout = computeGraphLayout(TREE_EMPTY);
    expect(layout.rows).toHaveLength(0);
    expect(layout.laneCount).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 10. Legacy nodes (branch_id null)
// ---------------------------------------------------------------------------

describe("legacy nodes", () => {
  const TREE_LEGACY: TreeOut = {
    root_id: 1,
    nodes: [
      node(2, null, 1, "2026-06-06T00:00:00Z", { is_head: true, is_immutable: false }),
      node(1, null, null, "2026-06-05T00:00:00Z", { is_immutable: true }),
    ],
    branches: [],
  };

  it("legacy nodes get color LANE_COLORS.legacy", () => {
    const layout = computeGraphLayout(TREE_LEGACY);
    for (const row of layout.rows) {
      expect(row.color).toBe(LANE_COLORS.legacy);
    }
  });

  it("legacy nodes do not crash and produce rows", () => {
    const layout = computeGraphLayout(TREE_LEGACY);
    expect(layout.rows).toHaveLength(2);
  });

  it("legacy nodes all share lane 0", () => {
    const layout = computeGraphLayout(TREE_LEGACY);
    for (const row of layout.rows) {
      expect(row.lane).toBe(0);
    }
  });
});

// ---------------------------------------------------------------------------
// 11. Main tip pill
// ---------------------------------------------------------------------------

describe("main tip pill", () => {
  it("main tip has pill text '★ main' and isMain=true", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const row = layout.rows.find((r) => r.node.id === 4)!; // working head
    expect(row.isBranchTip).toBe(true);
    expect(row.pill).not.toBeNull();
    expect(row.pill!.text).toBe("★ main");
    expect(row.pill!.isMain).toBe(true);
  });

  it("non-tip nodes have pill=null", () => {
    const layout = computeGraphLayout(TREE_WORKED);
    const nonTipIds = [1, 2, 3]; // root, v1.0, v1.1 — none are tips
    for (const id of nonTipIds) {
      const row = layout.rows.find((r) => r.node.id === id)!;
      expect(row.pill).toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// Adopted branch: is_main is the SOLE authority, NOT the branch name.
//
// Real-world case (root 8 "Olek"): a `copilot-proposal` branch was adopted as
// is_main, while the branch literally named "main" is is_main=false. The graph
// must treat the is_main branch as the active main (lane 0, star pill showing
// its real name), and the name "main" branch as an ordinary branch.
// ---------------------------------------------------------------------------

describe("adopted non-'main'-named branch", () => {
  // branch 2 "main" (is_main FALSE, head 8) ; branch 23 "with segments" (head 43) ;
  // branch 25 "copilot-proposal" (is_main TRUE, head 45)
  const TREE_ADOPTED: TreeOut = {
    root_id: 8,
    nodes: [
      node(45, 25, null, "2026-06-11T20:06:00Z", { is_head: true, created_by: "copilot" }),
      node(43, 23, null, "2026-06-11T07:15:00Z", { is_head: true, created_by: "human" }),
      node(42, 2, null, "2026-06-11T07:15:00Z", { is_immutable: true, created_by: "human" }),
      node(8, 2, 42, "2026-04-24T10:48:00Z", { is_head: true }),
    ],
    branches: [
      branch(2, "main", 8, false),
      branch(23, "with segments", 43, false),
      branch(25, "copilot-proposal", 45, true),
    ],
  };

  it("marks exactly ONE pill as the active main", () => {
    const layout = computeGraphLayout(TREE_ADOPTED);
    const mainPills = layout.rows.filter((r) => r.pill?.isMain);
    expect(mainPills).toHaveLength(1);
    expect(mainPills[0].node.branch_id).toBe(25); // copilot-proposal, the is_main one
  });

  it("the is_main branch is the active one even though it is not named 'main'", () => {
    const layout = computeGraphLayout(TREE_ADOPTED);
    const copilotTip = layout.rows.find((r) => r.node.id === 45)!;
    expect(copilotTip.pill?.isMain).toBe(true);
    expect(copilotTip.pill?.text).toContain("copilot-proposal");
    expect(copilotTip.lane).toBe(0);
    expect(copilotTip.color).toBe(LANE_COLORS.main);
  });

  it("the branch literally named 'main' but not is_main is an ordinary branch", () => {
    const layout = computeGraphLayout(TREE_ADOPTED);
    const namedMainTip = layout.rows.find((r) => r.node.id === 8)!;
    expect(namedMainTip.pill?.isMain).toBe(false);
    expect(namedMainTip.pill?.text).toContain("main");
    expect(namedMainTip.lane).not.toBe(0);
    expect(namedMainTip.color).not.toBe(LANE_COLORS.main);
  });
});
