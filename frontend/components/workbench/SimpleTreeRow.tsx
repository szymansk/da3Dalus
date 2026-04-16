"use client";

import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";

export interface SimpleTreeNode {
  id: string;
  label: string;
  level: number;
  expanded?: boolean;
  leaf?: boolean;
  muted?: boolean;
  selected?: boolean;
  chip?: string;
  annotation?: string;
  annotationPrimary?: boolean;
  onClick?: () => void;
  onDelete?: () => void;
  /** Optional per-row add action. Rendered only when provided (typically group rows only). */
  onAdd?: () => void;
  /** Tooltip for the add button; also used as a test hook via title="…". */
  addTitle?: string;
}

interface SimpleTreeRowProps {
  node: SimpleTreeNode;
  onToggle: () => void;
}

export function SimpleTreeRow({ node, onToggle }: SimpleTreeRowProps) {
  const indent = node.level * 20;

  function handleClick() {
    if (!node.leaf) onToggle();
    node.onClick?.();
  }

  return (
    <div
      className={`group flex w-full items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent cursor-pointer ${
        node.selected ? "bg-sidebar-accent font-semibold" : ""
      }`}
      style={{ paddingLeft: indent }}
      onClick={handleClick}
    >
      {!node.leaf ? (
        node.expanded ? (
          <ChevronDown size={12} className="shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight size={12} className="shrink-0 text-muted-foreground" />
        )
      ) : (
        <span className="w-3 shrink-0" />
      )}
      <span
        className={`truncate ${node.muted ? "text-[12px] text-muted-foreground" : "font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"}`}
      >
        {node.label}
      </span>
      {node.chip && (
        <span className="rounded bg-card-muted px-1.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-primary">
          {node.chip}
        </span>
      )}
      <span className="flex-1" />
      {node.annotation && (
        <span
          className={`font-[family-name:var(--font-jetbrains-mono)] text-[11px] ${node.annotationPrimary ? "text-primary" : "text-muted-foreground"}`}
        >
          {node.annotation}
        </span>
      )}
      {node.onAdd && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onAdd?.(); }}
          title={node.addTitle ?? "Add"}
          className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground group-hover:flex"
        >
          <Plus size={10} />
        </button>
      )}
      {node.onDelete && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onDelete?.(); }}
          className="hidden size-5 items-center justify-center rounded-full text-destructive group-hover:flex"
        >
          <Trash2 size={10} />
        </button>
      )}
    </div>
  );
}
