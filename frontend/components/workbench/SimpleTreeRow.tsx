"use client";

import { ChevronDown, ChevronRight } from "lucide-react";

export interface SimpleTreeNode {
  id: string;
  label: string;
  level: number;
  expanded?: boolean;
  leaf?: boolean;
  muted?: boolean;
  chip?: string;
  annotation?: string;
  annotationPrimary?: boolean;
}

interface SimpleTreeRowProps {
  node: SimpleTreeNode;
  onToggle: () => void;
}

export function SimpleTreeRow({ node, onToggle }: SimpleTreeRowProps) {
  const indent = node.level * 20;
  return (
    <button
      onClick={onToggle}
      style={{ paddingLeft: indent }}
      className="flex w-full items-center gap-1.5 rounded-lg py-1.5 pr-2 text-left hover:bg-sidebar-accent"
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
    </button>
  );
}
