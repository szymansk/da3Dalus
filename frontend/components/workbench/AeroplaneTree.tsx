"use client";

import { ChevronDown, ChevronRight, Plus } from "lucide-react";

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
}

const TREE_DATA: TreeNode[] = [
  { id: "ehawk", label: "eHawk", level: 0, expanded: true },
  {
    id: "main_wing",
    label: "main_wing",
    level: 1,
    expanded: true,
    ghost: "+ segment",
  },
  {
    id: "seg0",
    label: "segment 0 (root)",
    level: 2,
    expanded: true,
    selected: true,
  },
  {
    id: "seg0-root",
    label: "root_airfoil \u00b7 mh32",
    level: 3,
    leaf: true,
    muted: true,
  },
  {
    id: "seg0-tip",
    label: "tip_airfoil \u00b7 mh32",
    level: 3,
    leaf: true,
    muted: true,
  },
  {
    id: "seg0-dims",
    label: "length 20 mm \u00b7 sweep 0 mm",
    level: 3,
    leaf: true,
    muted: true,
    mono: true,
  },
  { id: "seg0-spars", label: "spars (3)", level: 3, expanded: false },
  { id: "seg1", label: "segment 1", level: 2, expanded: false },
  {
    id: "seg2",
    label: "segment 2",
    level: 2,
    expanded: false,
    chip: "AILERON",
  },
  {
    id: "seg3",
    label: "segment 3",
    level: 2,
    expanded: false,
    chip: "AILERON",
  },
  { id: "elevator", label: "elevator_wing", level: 1, expanded: false },
  { id: "fuselage", label: "fuselage", level: 1, expanded: false },
];

function TreeRow({ node }: { node: TreeNode }) {
  const indent = node.level * 20;
  const isLeaf = node.leaf;

  return (
    <div
      className={`flex items-center gap-2 rounded-[--radius-s] py-1.5 hover:bg-sidebar-accent ${
        node.selected ? "bg-sidebar-accent font-semibold" : ""
      }`}
      style={{ paddingLeft: `${indent}px` }}
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
        <span className="text-[12px] text-muted-foreground opacity-50">
          {node.ghost}
        </span>
      )}
    </div>
  );
}

export function AeroplaneTree() {
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
        {TREE_DATA.map((node) => (
          <TreeRow key={node.id} node={node} />
        ))}
      </div>
    </div>
  );
}
