"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWing } from "@/hooks/useWings";
import type { XSec } from "@/hooks/useWings";
import { API_BASE } from "@/lib/fetcher";

interface TreeNode {
  id: string;
  label: string;
  level: number;
  expanded?: boolean;
  selected?: boolean;
  leaf?: boolean;
  mono?: boolean;
  muted?: boolean;
  chip?: string;
  ghost?: string;
  onGhostClick?: () => void;
  onClick?: () => void;
}

function buildWingNodes(
  wingName: string,
  wing: { name: string; symmetric: boolean; x_secs: XSec[] } | null,
  selectedWing: string | null,
  selectedXsecIndex: number | null,
  expandedSet: Set<string>,
  selectWing: (name: string | null) => void,
  selectXsec: (index: number | null) => void,
  onAddSegment?: (wingName: string) => void,
): TreeNode[] {
  const nodes: TreeNode[] = [];

  const wingExpanded = expandedSet.has(`wing-${wingName}`);
  nodes.push({
    id: `wing-${wingName}`,
    label: wingName,
    level: 1,
    expanded: wingExpanded,
    ghost: "+ segment",
    onGhostClick: () => onAddSegment?.(wingName),
    onClick: () => selectWing(wingName),
  });

  if (!wingExpanded) return nodes;

  // Wing is expanded but data not loaded yet (SWR fetching)
  if (!wing || wing.name !== wingName) {
    nodes.push({
      id: `${wingName}-loading`,
      label: "Loading segments…",
      level: 2,
      leaf: true,
      muted: true,
    });
    return nodes;
  }

  wing.x_secs.forEach((xsec: XSec, i: number) => {
    const segId = `${wingName}-seg${i}`;
    const isSelected = selectedWing === wingName && selectedXsecIndex === i;
    const segExpanded = expandedSet.has(segId);
    const chipLabel =
      xsec.trailing_edge_device &&
      typeof xsec.trailing_edge_device === "object" &&
      "name" in xsec.trailing_edge_device
        ? String(xsec.trailing_edge_device.name).toUpperCase()
        : xsec.control_surface &&
            typeof xsec.control_surface === "object" &&
            "name" in xsec.control_surface
          ? String(xsec.control_surface.name).toUpperCase()
          : undefined;

    nodes.push({
      id: segId,
      label: i === 0 ? `segment ${i} (root)` : `segment ${i}`,
      level: 2,
      expanded: segExpanded,
      selected: isSelected,
      chip: chipLabel,
      onClick: () => {
        selectWing(wingName);
        selectXsec(i);
      },
    });

    if (segExpanded) {
      nodes.push({
        id: `${segId}-airfoil`,
        label: `airfoil \u00b7 ${xsec.airfoil}`,
        level: 3,
        leaf: true,
        muted: true,
      });
      nodes.push({
        id: `${segId}-chord`,
        label: `chord ${xsec.chord}`,
        level: 3,
        leaf: true,
        muted: true,
        mono: true,
      });
      nodes.push({
        id: `${segId}-twist`,
        label: `twist ${xsec.twist}\u00b0`,
        level: 3,
        leaf: true,
        muted: true,
        mono: true,
      });
      const spareCount = Array.isArray(xsec.spare_list)
        ? xsec.spare_list.length
        : 0;
      if (spareCount > 0) {
        nodes.push({
          id: `${segId}-spars`,
          label: `spars (${spareCount})`,
          level: 3,
          expanded: false,
        });
      }
    }
  });

  return nodes;
}

interface AeroplaneTreeProps {
  aeroplaneId: string | null;
  wingNames: string[];
  aeroplaneName?: string;
}

export function AeroplaneTree({
  aeroplaneId,
  wingNames,
  aeroplaneName,
}: AeroplaneTreeProps) {
  const { selectedWing, selectedXsecIndex, selectWing, selectXsec } =
    useAeroplaneContext();
  const { wing, isLoading, mutate: mutateWing } = useWing(aeroplaneId, selectedWing);

  async function handleAddSegment(wingName: string) {
    if (!aeroplaneId) return;
    // Add a new x_sec at the end of the wing
    const xsecCount = wing?.x_secs.length ?? 0;
    const lastXsec = wing?.x_secs[xsecCount - 1];
    const newXsec = {
      xyz_le: [
        (lastXsec?.xyz_le[0] ?? 0),
        (lastXsec?.xyz_le[1] ?? 0) + 0.1,
        (lastXsec?.xyz_le[2] ?? 0),
      ],
      chord: lastXsec?.chord ?? 0.1,
      twist: 0,
      airfoil: lastXsec?.airfoil ?? "naca0012",
    };
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecCount}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newXsec),
      },
    );
    if (res.ok) {
      await mutateWing();
      selectXsec(xsecCount);
    }
  }

  const [expandedSet, setExpandedSet] = useState<Set<string>>(() => {
    const s = new Set<string>();
    s.add("root");
    if (wingNames.length > 0) s.add(`wing-${wingNames[0]}`);
    return s;
  });

  function toggleExpand(nodeId: string) {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }

  const treeData: TreeNode[] = [];

  // Root node
  const rootExpanded = expandedSet.has("root");
  treeData.push({
    id: "root",
    label: aeroplaneName ?? "Aeroplane",
    level: 0,
    expanded: rootExpanded,
  });

  if (rootExpanded) {
    for (const wn of wingNames) {
      const wingNodes = buildWingNodes(
        wn,
        wing,
        selectedWing,
        selectedXsecIndex,
        expandedSet,
        selectWing,
        selectXsec,
        handleAddSegment,
      );
      treeData.push(...wingNodes);
    }
  }

  return (
    <div className="rounded-[--radius-m] border border-border bg-card p-3 px-4">
      {/* Header */}
      <div className="mb-2 flex items-center">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Aeroplane Tree
        </span>
        <div className="flex-1" />
        <button className="flex h-6 w-6 items-center justify-center rounded-[--radius-s] text-muted-foreground hover:bg-sidebar-accent">
          <Plus size={14} />
        </button>
      </div>

      {/* Tree rows */}
      <div className="flex flex-col gap-0.5">
        {isLoading && wingNames.length === 0 ? (
          <span className="text-[13px] text-muted-foreground">Loading...</span>
        ) : (
          treeData.map((node) => (
            <TreeRow
              key={node.id}
              node={node}
              onToggle={() => toggleExpand(node.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function TreeRow({
  node,
  onToggle,
}: {
  node: TreeNode;
  onToggle: () => void;
}) {
  const indent = node.level * 20;
  const isLeaf = node.leaf;

  function handleClick() {
    if (!isLeaf) {
      onToggle();
    }
    node.onClick?.();
  }

  return (
    <div
      className={`flex items-center gap-2 rounded-[--radius-s] py-1.5 hover:bg-sidebar-accent ${
        node.selected ? "bg-sidebar-accent font-semibold" : ""
      }`}
      style={{ paddingLeft: `${indent}px`, cursor: "pointer" }}
      onClick={handleClick}
    >
      {!isLeaf && (
        <span className="flex h-3 w-3 shrink-0 items-center justify-center text-muted-foreground">
          {node.expanded ? (
            <ChevronDown size={12} />
          ) : (
            <ChevronRight size={12} />
          )}
        </span>
      )}
      {isLeaf && <span className="w-3 shrink-0" />}

      <span
        className={`text-[13px] ${
          node.muted
            ? "text-[12px] text-muted-foreground"
            : "text-foreground"
        } ${node.mono ? "font-[family-name:var(--font-jetbrains-mono)]" : ""}`}
      >
        {node.label}
      </span>

      {node.chip && (
        <span className="rounded bg-card-muted px-1.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-primary">
          {node.chip}
        </span>
      )}

      {node.ghost && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            node.onGhostClick?.();
          }}
          className="text-[12px] text-muted-foreground opacity-50 hover:opacity-100 hover:text-primary">
          {node.ghost}
        </button>
      )}
    </div>
  );
}
