"use client";

import { useDraggable, useDroppable } from "@dnd-kit/core";
import { ChevronDown, ChevronRight, Pencil, Plus, Scale, Trash2 } from "lucide-react";

export type SimpleTreeWeightStatus = "valid" | "partial" | "invalid";

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
  /** Optional per-row edit action — opens a property modal. Rendered only when provided. */
  onEdit?: () => void;
  /** Tooltip/test hook for the edit button. Defaults to "Edit {label}". */
  editTitle?: string;
  /** Weight status (gh#78). Renders a colored scale icon when set. */
  weightStatus?: SimpleTreeWeightStatus;
  /** Tooltip text for the weight icon. */
  weightTooltip?: string;
}

interface SimpleTreeRowProps {
  node: SimpleTreeNode;
  onToggle: () => void;
}

export function SimpleTreeRow({ node, onToggle }: SimpleTreeRowProps) {
  const indent = node.level * 20;

  // dnd-kit hooks: each row is BOTH draggable (source) and droppable (target).
  // We share the same id space so the parent's onDragEnd can resolve the move
  // through the existing tree data.
  const dndId = `node-${node.id}`;
  const { attributes, listeners, setNodeRef: setDragRef, isDragging } = useDraggable({
    id: dndId,
  });
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: dndId });

  function setRefs(el: HTMLDivElement | null) {
    setDragRef(el);
    setDropRef(el);
  }

  function handleClick() {
    if (!node.leaf) onToggle();
    node.onClick?.();
  }

  return (
    <div
      ref={setRefs}
      {...attributes}
      {...listeners}
      aria-roledescription="sortable"
      className={`group flex w-full items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent cursor-pointer ${
        node.selected ? "bg-sidebar-accent font-semibold" : ""
      } ${isOver ? "ring-2 ring-primary" : ""} ${isDragging ? "opacity-40" : ""}`}
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
      {node.weightStatus && (
        <span
          title={node.weightTooltip ?? `Weight: ${node.weightStatus}`}
          className={
            node.weightStatus === "valid"
              ? "text-emerald-500"
              : node.weightStatus === "partial"
              ? "text-amber-500"
              : "text-red-500"
          }
          data-weight-status={node.weightStatus}
        >
          <Scale size={11} />
        </span>
      )}
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
      {node.onEdit && (
        <button
          onClick={(e) => { e.stopPropagation(); node.onEdit?.(); }}
          title={node.editTitle ?? `Edit ${node.label}`}
          className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground group-hover:flex"
        >
          <Pencil size={10} />
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
