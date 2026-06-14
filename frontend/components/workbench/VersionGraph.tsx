"use client";

/**
 * VersionGraph — renders the full GitKraken-style version graph (gh-961).
 *
 * Calls `computeGraphLayout(tree)` and maps the resulting rows to
 * `GraphRow` components. Thin render layer; all geometry is handled by
 * the pure layout util.
 */

import { useMemo } from "react";
import { computeGraphLayout } from "@/lib/versionGraphLayout";
import { GraphRow } from "@/components/workbench/GraphRow";
import type { TreeOut } from "@/types/versioning";

export interface VersionGraphProps {
  readonly tree: TreeOut;
  readonly currentHeadId: number | null;
  readonly selectedNodeId: number | null;
  readonly compareSet: Set<number>;
  readonly onSelectNode: (nodeId: number) => void;
  readonly onCheckNode: (nodeId: number) => void;
  /**
   * When provided, only nodes whose branch id is in this set are laid out
   * (legacy null-branch nodes are always kept). Undefined = show all branches.
   */
  readonly visibleBranchIds?: ReadonlySet<number>;
}

export function VersionGraph({
  tree,
  currentHeadId,
  selectedNodeId,
  compareSet,
  onSelectNode,
  onCheckNode,
  visibleBranchIds,
}: VersionGraphProps) {
  // O(n²) worst case — memoise so it doesn't recompute on every parent
  // re-render (e.g. each compare-checkbox tick). SWR keeps `tree` referentially
  // stable between unchanged revalidations, so the cache hit rate is high.
  const layout = useMemo(
    () => computeGraphLayout(tree, { visibleBranchIds }),
    [tree, visibleBranchIds],
  );

  if (layout.rows.length === 0) {
    return (
      <p className="px-4 py-4 text-[12px] text-muted-foreground">
        No branches selected.
      </p>
    );
  }

  return (
    <div role="grid" aria-label="Version graph" className="flex flex-col divide-y divide-border/40">
      {layout.rows.map((row) => (
        <GraphRow
          key={row.node.id}
          row={row}
          laneCount={layout.laneCount}
          isSelected={selectedNodeId === row.node.id}
          isChecked={compareSet.has(row.node.id)}
          currentHeadId={currentHeadId}
          onSelect={onSelectNode}
          onCheck={onCheckNode}
        />
      ))}
    </div>
  );
}
