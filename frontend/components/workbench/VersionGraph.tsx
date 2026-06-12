"use client";

/**
 * VersionGraph — renders the full GitKraken-style version graph (gh-961).
 *
 * Calls `computeGraphLayout(tree)` and maps the resulting rows to
 * `GraphRow` components. Thin render layer; all geometry is handled by
 * the pure layout util.
 */

import React from "react";
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
}

export function VersionGraph({
  tree,
  currentHeadId,
  selectedNodeId,
  compareSet,
  onSelectNode,
  onCheckNode,
}: VersionGraphProps) {
  const layout = computeGraphLayout(tree);

  if (layout.rows.length === 0) {
    return (
      <p className="px-4 py-4 text-[12px] text-muted-foreground">
        No version history yet. Use the Save button to create your first snapshot.
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
