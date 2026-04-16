"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { TreeCard } from "@/components/workbench/TreeCard";
import { SimpleTreeRow, type SimpleTreeNode } from "@/components/workbench/SimpleTreeRow";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useComponentTree, addTreeNode, deleteTreeNode, type ComponentTreeNode } from "@/hooks/useComponentTree";

function flattenTree(
  nodes: ComponentTreeNode[],
  level: number,
  expanded: Set<string>,
  onSelect: (node: ComponentTreeNode) => void,
  onDelete: (node: ComponentTreeNode) => void,
  selectedId: number | null,
): SimpleTreeNode[] {
  const result: SimpleTreeNode[] = [];
  for (const node of nodes) {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expanded.has(String(node.id));
    result.push({
      id: String(node.id),
      label: node.name,
      level,
      expanded: hasChildren ? isExpanded : undefined,
      leaf: !hasChildren,
      selected: node.id === selectedId,
      chip: node.node_type === "cots" ? "COTS" : node.node_type === "cad_shape" ? "CAD" : undefined,
      annotation: node.weight_override_g != null ? `${node.weight_override_g}g` : undefined,
      onClick: () => onSelect(node),
      onDelete: () => onDelete(node),
    });
    if (hasChildren && isExpanded) {
      result.push(...flattenTree(node.children, level + 1, expanded, onSelect, onDelete, selectedId));
    }
  }
  return result;
}

export function ComponentTree() {
  const { aeroplaneId } = useAeroplaneContext();
  const { tree, mutate } = useComponentTree(aeroplaneId);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleSelect = (node: ComponentTreeNode) => {
    setSelectedNodeId(node.id);
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

  const handleAddGroup = async () => {
    if (!aeroplaneId) return;
    const name = prompt("Group name?");
    if (!name) return;
    try {
      await addTreeNode(aeroplaneId, { node_type: "group", name });
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Add failed");
    }
  };

  const rows = flattenTree(tree, 0, expanded, handleSelect, handleDelete, selectedNodeId);

  return (
    <TreeCard
      title="Component Tree"
      actions={
        <button
          onClick={handleAddGroup}
          className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title="Add group"
        >
          <Plus size={14} />
        </button>
      }
    >
      <div className="flex flex-col gap-0.5">
        {rows.length === 0 ? (
          <p className="py-4 text-center text-[11px] text-muted-foreground">
            No components yet. Add a group or assign COTS parts.
          </p>
        ) : (
          rows.map((node) => (
            <SimpleTreeRow key={node.id} node={node} onToggle={() => toggle(node.id)} />
          ))
        )}
      </div>
    </TreeCard>
  );
}
