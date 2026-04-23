"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
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
import { useAeroplanes } from "@/hooks/useAeroplanes";
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

/**
 * Sentinel ID for the synthesised root row (labelled with the aeroplane's
 * name). This row does not exist in the backend `component_tree` table — it
 * is a purely visual container so all real roots (`wing`, user groups, etc.)
 * nest under a single aeroplane-named node instead of floating loose. A
 * non-numeric string keeps it out of the way of real numeric node IDs in
 * dnd-kit ids and the `expanded` Set.
 */
export const VIRTUAL_ROOT_ID = "__root__";

interface FlattenCallbacks {
  onSelect: (node: ComponentTreeNode) => void;
  onDelete: (node: ComponentTreeNode) => void;
  onAdd: (node: ComponentTreeNode) => void;
  onEdit: (node: ComponentTreeNode) => void;
}

function weightTooltip(node: ComponentTreeNode): string {
  const source = node.own_weight_source ?? "none";
  const own = node.own_weight_g;
  const total = node.total_weight_g ?? 0;
  const status = node.weight_status ?? "invalid";
  const ownStr = own != null ? `${own.toFixed(1)}g` : "—";
  const sourceLabel: Record<string, string> = {
    override: "manual override",
    cots: "from COTS catalog",
    calculated: "calculated from volume + material",
    none: "no own weight",
  };
  if (status === "invalid") {
    return "Weight unknown — neither weight_override_g is set nor can it be calculated from material + volume (or COTS mass).";
  }
  return `Own: ${ownStr} (${sourceLabel[source]}). Total (with children): ${total.toFixed(1)}g.`;
}

/** Aggregate weight status for the root-level indicator next to the tree title. */
function aggregateRootStatus(
  roots: ComponentTreeNode[],
): { status: "valid" | "partial" | "invalid"; total: number } {
  if (roots.length === 0) return { status: "invalid", total: 0 };
  const total = roots.reduce((sum, r) => sum + (r.total_weight_g ?? 0), 0);
  const statuses = roots.map((r) => r.weight_status ?? "invalid");
  if (statuses.every((s) => s === "valid")) return { status: "valid", total };
  if (statuses.every((s) => s === "invalid")) return { status: "invalid", total };
  return { status: "partial", total };
}

/** Weight annotation string for a single tree node. */
function nodeAnnotation(node: ComponentTreeNode): string | undefined {
  const totalG = node.total_weight_g;
  if (totalG != null && totalG > 0) return `${totalG.toFixed(1)}g`;
  if (node.weight_override_g != null) return `${node.weight_override_g}g`;
  return undefined;
}

/** Node-type chip label for the tree row badge. */
function nodeChip(node: ComponentTreeNode): string | undefined {
  if (node.node_type === "cots") return "COTS";
  if (node.node_type === "cad_shape") return "CAD";
  return undefined;
}

function toSimpleTreeNode(
  node: ComponentTreeNode,
  level: number,
  isExpanded: boolean,
  cb: FlattenCallbacks,
  selectedId: number | null,
): SimpleTreeNode {
  const hasChildren = node.children && node.children.length > 0;
  const isGroup = node.node_type === "group";
  return {
    id: String(node.id),
    label: node.name,
    level,
    expanded: hasChildren ? isExpanded : undefined,
    leaf: !hasChildren,
    selected: node.id === selectedId,
    chip: nodeChip(node),
    annotation: nodeAnnotation(node),
    onClick: () => cb.onSelect(node),
    onDelete: () => cb.onDelete(node),
    onAdd: isGroup ? () => cb.onAdd(node) : undefined,
    addTitle: isGroup ? `Add to ${node.name}` : undefined,
    onEdit: () => cb.onEdit(node),
    editTitle: `Edit ${node.name}`,
    weightStatus: node.weight_status,
    weightTooltip: weightTooltip(node),
  };
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
    result.push(toSimpleTreeNode(node, level, isExpanded, cb, selectedId));
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

function NewGroupInput({ onSubmit, onCancel }: Readonly<NewGroupInputProps>) {
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
}: Readonly<ComponentTreeProps> = {}) {
  const { aeroplaneId } = useAeroplaneContext();
  const { tree, mutate } = useComponentTree(aeroplaneId);
  const { aeroplanes } = useAeroplanes();
  // Virtual root starts expanded by default so all real tree rows remain
  // visible on first render. Users can collapse it to hide everything — the
  // root row itself (with label + aggregated weight) always stays visible.
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set([VIRTUAL_ROOT_ID]),
  );
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [addFlow, setAddFlow] = useState<AddFlowStage>({ kind: "idle" });

  const aeroplaneName =
    aeroplanes.find((a) => a.id === aeroplaneId)?.name ?? "Aeroplane";

  // Pointer sensor with a small activation distance avoids hijacking simple
  // clicks (open menu, select node) for drags. Touch sensor brings drag-and-
  // drop to mobile.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
  );

  async function moveToRoot(activeId: number) {
    mutate();
    try {
      await moveTreeNode(aeroplaneId, activeId, {
        new_parent_id: null,
        sort_index: tree.length,
      });
      mutate();
    } catch (err) {
      mutate();
      if (typeof window !== "undefined") {
        alert(err instanceof Error ? err.message : "Move failed");
      }
    }
  }

  function onDragEnd(event: DragEndEvent) {
    if (!aeroplaneId) return;
    const activeStr = String(event.active.id).replace(/^node-/, "");
    const overStr = event.over
      ? String(event.over.id).replace(/^node-/, "")
      : null;

    if (activeStr === VIRTUAL_ROOT_ID) return;

    const activeId = Number(activeStr);
    if (Number.isNaN(activeId)) return;

    if (overStr === VIRTUAL_ROOT_ID) {
      void moveToRoot(activeId);
      return;
    }

    const overId = overStr ? Number(overStr) : null;
    if (overId !== null && Number.isNaN(overId)) return;
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

  const rootAgg = aggregateRootStatus(tree);
  const virtualExpanded = expanded.has(VIRTUAL_ROOT_ID);

  // Real tree rows are indented one level deeper so they nest visually under
  // the virtual root. They are only materialised when the virtual root is
  // expanded — collapsing the root hides the whole tree (native tree UX).
  const childRows = virtualExpanded
    ? flattenTree(
        tree,
        1,
        expanded,
        {
          onSelect: handleSelect,
          onDelete: handleDelete,
          onAdd: openAddMenu,
          onEdit: (n) => onNodeEditRequested?.(n),
        },
        selectedNodeId,
      )
    : [];

  const virtualRootRow: SimpleTreeNode = {
    id: VIRTUAL_ROOT_ID,
    label: aeroplaneName,
    level: 0,
    expanded: virtualExpanded,
    leaf: false,
    // No onDelete / onEdit / onClick — the row is a display container. The
    // chevron-toggle is handled by SimpleTreeRow's built-in `!leaf` click
    // behaviour. `onAdd` keeps the "+ to root" entry point available on
    // hover, now attached to the root row instead of the panel header.
    onAdd: openRootAddMenu,
    addTitle: `Add to ${aeroplaneName}`,
    weightStatus: rootAgg.status,
    weightTooltip:
      rootAgg.status === "valid"
        ? "All nodes have a valid weight"
        : rootAgg.status === "partial"
        ? "Some nodes have no weight and are counted as 0"
        : "No node in the tree has a valid weight",
    annotation:
      rootAgg.total > 0 ? `${rootAgg.total.toFixed(1)}g` : undefined,
    annotationPrimary: true,
  };

  const rows: SimpleTreeNode[] = [virtualRootRow, ...childRows];

  return (
    <>
      <TreeCard title="Component Tree">
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="flex flex-col gap-0.5">
          {rows.map((node) => (
            <SimpleTreeRow key={node.id} node={node} onToggle={() => toggle(node.id)} />
          ))}

          {virtualExpanded && tree.length === 0 && (
            <p className="py-4 text-center text-[11px] text-muted-foreground">
              No components yet. Add a group or assign a component.
            </p>
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
