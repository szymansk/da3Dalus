"use client";

import { useState } from "react";
import { Plus, Check, X } from "lucide-react";
import {
  DndContext,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { TreeCard } from "@/components/workbench/TreeCard";
import { SimpleTreeRow, type SimpleTreeNode } from "@/components/workbench/SimpleTreeRow";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import {
  useComponentTree,
  addTreeNode,
  deleteTreeNode,
  moveTreeNode,
  type ComponentTreeNode,
} from "@/hooks/useComponentTree";
import { GroupAddMenu } from "@/components/workbench/GroupAddMenu";
import { CotsPickerDialog } from "@/components/workbench/CotsPickerDialog";
import { ConstructionPartPickerDialog } from "@/components/workbench/ConstructionPartPickerDialog";
import type { Component } from "@/hooks/useComponents";
import type { ConstructionPart } from "@/hooks/useConstructionParts";
import { computeMoveResult } from "@/lib/treeDnd";

/**
 * Pure drop handler — separated so it can be unit-tested without simulating
 * mouse events. Returns silently on invalid drops (cycle, leaf-as-target,
 * drop-on-self, drop-outside). On success: optimistic mutate + API call +
 * rollback mutate on failure.
 */
export interface HandleDragEndArgs {
  activeId: number;
  overId: number | null;
  tree: ComponentTreeNode[];
  aeroplaneId: string;
  moveFn: typeof moveTreeNode;
  mutateFn: () => void;
}

export async function handleDragEnd({
  activeId,
  overId,
  tree,
  aeroplaneId,
  moveFn,
  mutateFn,
}: HandleDragEndArgs): Promise<void> {
  if (overId == null) return;
  const result = computeMoveResult(tree, activeId, overId, "into");
  if (!result) return;

  // Optimistic refetch trigger (UI updates after the server confirms).
  mutateFn();
  try {
    await moveFn(aeroplaneId, activeId, {
      new_parent_id: result.newParentId,
      sort_index: result.sortIndex,
    });
    mutateFn();
  } catch (err) {
    // Rollback: refetch from server to discard any client-side optimistic state.
    mutateFn();
    if (typeof window !== "undefined") {
      alert(err instanceof Error ? err.message : "Move failed");
    }
  }
}

type AddFlowStage =
  | { kind: "idle" }
  | { kind: "menu"; parentId: number | null; parentName: string }
  | { kind: "newGroup"; parentId: number | null; parentName: string }
  | { kind: "cotsPicker"; parentId: number | null; parentName: string }
  | { kind: "constructionPartsPicker"; parentId: number | null; parentName: string };

interface FlattenCallbacks {
  onSelect: (node: ComponentTreeNode) => void;
  onDelete: (node: ComponentTreeNode) => void;
  onAdd: (node: ComponentTreeNode) => void;
  onEdit: (node: ComponentTreeNode) => void;
}

function flattenTree(
  nodes: ComponentTreeNode[],
  level: number,
  expanded: Set<string>,
  cb: FlattenCallbacks,
  selectedId: number | null,
): SimpleTreeNode[] {
  const result: SimpleTreeNode[] = [];
  for (const node of nodes) {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expanded.has(String(node.id));
    const isGroup = node.node_type === "group";
    result.push({
      id: String(node.id),
      label: node.name,
      level,
      expanded: hasChildren ? isExpanded : undefined,
      leaf: !hasChildren,
      selected: node.id === selectedId,
      chip: node.node_type === "cots" ? "COTS" : node.node_type === "cad_shape" ? "CAD" : undefined,
      annotation: node.weight_override_g != null ? `${node.weight_override_g}g` : undefined,
      onClick: () => cb.onSelect(node),
      onDelete: () => cb.onDelete(node),
      onAdd: isGroup ? () => cb.onAdd(node) : undefined,
      addTitle: isGroup ? `Add to ${node.name}` : undefined,
      onEdit: () => cb.onEdit(node),
      editTitle: `Edit ${node.name}`,
    });
    if (hasChildren && isExpanded) {
      result.push(...flattenTree(node.children, level + 1, expanded, cb, selectedId));
    }
  }
  return result;
}

interface NewGroupInputProps {
  onSubmit: (name: string) => void;
  onCancel: () => void;
}

function NewGroupInput({ onSubmit, onCancel }: NewGroupInputProps) {
  const [value, setValue] = useState("");

  function trySubmit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  }

  return (
    <div className="flex items-center gap-1.5 rounded-xl border border-primary bg-card px-2 py-1.5">
      <input
        autoFocus
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") trySubmit();
          if (e.key === "Escape") onCancel();
        }}
        placeholder="Group name..."
        className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
      />
      <button
        onClick={trySubmit}
        className="flex size-5 items-center justify-center rounded-full text-primary hover:bg-sidebar-accent"
        aria-label="Create group"
      >
        <Check size={12} />
      </button>
      <button
        onClick={onCancel}
        className="flex size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
        aria-label="Cancel"
      >
        <X size={12} />
      </button>
    </div>
  );
}

interface ComponentTreeProps {
  /** Invoked whenever the selection changes — null when a node is deselected. */
  onNodeSelected?: (node: ComponentTreeNode | null) => void;
  /** Invoked when the user clicks the pencil icon on a row; opens a property modal. */
  onNodeEditRequested?: (node: ComponentTreeNode) => void;
}

export function ComponentTree({
  onNodeSelected,
  onNodeEditRequested,
}: ComponentTreeProps = {}) {
  const { aeroplaneId } = useAeroplaneContext();
  const { tree, mutate } = useComponentTree(aeroplaneId);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [addFlow, setAddFlow] = useState<AddFlowStage>({ kind: "idle" });

  // Pointer sensor with a small activation distance avoids hijacking simple
  // clicks (open menu, select node) for drags. Touch sensor brings drag-and-
  // drop to mobile.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
  );

  function onDragEnd(event: DragEndEvent) {
    if (!aeroplaneId) return;
    const activeId = Number(String(event.active.id).replace(/^node-/, ""));
    const overId = event.over ? Number(String(event.over.id).replace(/^node-/, "")) : null;
    if (Number.isNaN(activeId)) return;
    void handleDragEnd({
      activeId,
      overId,
      tree,
      aeroplaneId,
      moveFn: moveTreeNode,
      mutateFn: mutate,
    });
  }

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelect = (node: ComponentTreeNode) => {
    setSelectedNodeId(node.id);
    onNodeSelected?.(node);
  };

  const handleDelete = async (node: ComponentTreeNode) => {
    if (!aeroplaneId) return;
    if (!confirm(`Delete "${node.name}"?`)) return;
    try {
      await deleteTreeNode(aeroplaneId, node.id);
      mutate();
      if (selectedNodeId === node.id) setSelectedNodeId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const openAddMenu = (node: ComponentTreeNode) => {
    // Auto-expand the target group so a newly created child is visible right away.
    setExpanded((prev) => {
      const next = new Set(prev);
      next.add(String(node.id));
      return next;
    });
    setAddFlow({ kind: "menu", parentId: node.id, parentName: node.name });
  };

  const openRootAddMenu = () => {
    setAddFlow({ kind: "menu", parentId: null, parentName: "root" });
  };

  const handleCreateGroup = async (name: string) => {
    if (!aeroplaneId) return;
    const parentId = addFlow.kind === "newGroup" ? addFlow.parentId : null;
    try {
      await addTreeNode(aeroplaneId, {
        parent_id: parentId,
        node_type: "group",
        name,
      });
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Add failed");
    } finally {
      setAddFlow({ kind: "idle" });
    }
  };

  const handleAssignCots = async (component: Component) => {
    if (!aeroplaneId) return;
    const parentId = addFlow.kind === "cotsPicker" ? addFlow.parentId : null;
    try {
      await addTreeNode(aeroplaneId, {
        parent_id: parentId,
        node_type: "cots",
        name: component.name,
        component_id: component.id,
        quantity: 1,
      });
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Assign failed");
    } finally {
      setAddFlow({ kind: "idle" });
    }
  };

  const handleAssignConstructionPart = async (part: ConstructionPart) => {
    if (!aeroplaneId) return;
    const parentId =
      addFlow.kind === "constructionPartsPicker" ? addFlow.parentId : null;
    try {
      // Backend's add_node (N1 snapshot logic) copies volume/area/material
      // from the referenced part when construction_part_id is set and the
      // corresponding fields are not explicitly passed.
      await addTreeNode(aeroplaneId, {
        parent_id: parentId,
        node_type: "cad_shape",
        name: part.name,
        construction_part_id: part.id,
      });
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Assign failed");
    } finally {
      setAddFlow({ kind: "idle" });
    }
  };

  const rows = flattenTree(
    tree,
    0,
    expanded,
    {
      onSelect: handleSelect,
      onDelete: handleDelete,
      onAdd: openAddMenu,
      onEdit: (n) => onNodeEditRequested?.(n),
    },
    selectedNodeId,
  );

  return (
    <>
      <TreeCard
        title="Component Tree"
        actions={
          <button
            onClick={openRootAddMenu}
            className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            title="Add to root"
          >
            <Plus size={14} />
          </button>
        }
      >
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="flex flex-col gap-0.5">
          {rows.length === 0 ? (
            <p className="py-4 text-center text-[11px] text-muted-foreground">
              No components yet. Add a group or assign a component.
            </p>
          ) : (
            rows.map((node) => (
              <SimpleTreeRow key={node.id} node={node} onToggle={() => toggle(node.id)} />
            ))
          )}

          {addFlow.kind === "newGroup" && (
            <div className="px-1 py-1">
              <NewGroupInput
                onSubmit={handleCreateGroup}
                onCancel={() => setAddFlow({ kind: "idle" })}
              />
            </div>
          )}
        </div>
        </DndContext>
      </TreeCard>

      {addFlow.kind === "menu" && (
        <div
          className="fixed inset-0 z-40 bg-black/40"
          onClick={() => setAddFlow({ kind: "idle" })}
        >
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
            <GroupAddMenu
              groupName={addFlow.parentName}
              onNewGroup={() =>
                setAddFlow({
                  kind: "newGroup",
                  parentId: addFlow.parentId,
                  parentName: addFlow.parentName,
                })
              }
              onAssignCots={() =>
                setAddFlow({
                  kind: "cotsPicker",
                  parentId: addFlow.parentId,
                  parentName: addFlow.parentName,
                })
              }
              onAssignConstructionPart={() =>
                setAddFlow({
                  kind: "constructionPartsPicker",
                  parentId: addFlow.parentId,
                  parentName: addFlow.parentName,
                })
              }
              onClose={() => setAddFlow({ kind: "idle" })}
              constructionPartsEnabled={true}
            />
          </div>
        </div>
      )}

      <CotsPickerDialog
        open={addFlow.kind === "cotsPicker"}
        onClose={() => setAddFlow({ kind: "idle" })}
        onSelect={handleAssignCots}
        targetGroupName={addFlow.kind === "cotsPicker" ? addFlow.parentName : undefined}
      />

      <ConstructionPartPickerDialog
        open={addFlow.kind === "constructionPartsPicker"}
        aeroplaneId={aeroplaneId ?? ""}
        onClose={() => setAddFlow({ kind: "idle" })}
        onSelect={handleAssignConstructionPart}
        targetGroupName={
          addFlow.kind === "constructionPartsPicker" ? addFlow.parentName : undefined
        }
      />
    </>
  );
}
