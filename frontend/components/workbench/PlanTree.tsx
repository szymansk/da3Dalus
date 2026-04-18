"use client";

import { useState, useMemo, useCallback } from "react";
import {
  DndContext,
  useSensor,
  useSensors,
  PointerSensor,
  TouchSensor,
  type DragEndEvent,
} from "@dnd-kit/core";
import { Plus } from "lucide-react";
import { TreeCard } from "./TreeCard";
import { SimpleTreeRow, type SimpleTreeNode } from "./SimpleTreeRow";

export interface PlanStepNode {
  $TYPE: string;
  creator_id: string;
  [key: string]: unknown;
  successors?: PlanStepNode[];
}

interface PlanTreeProps {
  planName: string;
  treeJson: PlanStepNode | null;
  stepCount: number;
  selectedStepPath: string | null;
  onSelectStep: (path: string, node: PlanStepNode) => void;
  onDeleteStep: (path: string) => void;
  onAddStep: () => void;
  onReorder: (fromPath: string, toPath: string) => void;
}

function flattenSteps(
  node: PlanStepNode,
  path: string,
  level: number,
  expanded: Set<string>,
  selectedPath: string | null,
  onSelect: (path: string, node: PlanStepNode) => void,
  onDelete: (path: string) => void,
): SimpleTreeNode[] {
  const successors = node.successors ?? [];
  const isLeaf = successors.length === 0;
  const isExpanded = expanded.has(path);

  const row: SimpleTreeNode = {
    id: path,
    label: node.creator_id ?? node.$TYPE ?? "Step",
    level,
    leaf: isLeaf,
    expanded: isExpanded,
    selected: path === selectedPath,
    chip: node.$TYPE?.replace("Creator", ""),
    onClick: () => onSelect(path, node),
    onDelete: () => onDelete(path),
  };

  const rows: SimpleTreeNode[] = [row];

  if (!isLeaf && isExpanded) {
    successors.forEach((child, i) => {
      rows.push(
        ...flattenSteps(
          child,
          `${path}.${i}`,
          level + 1,
          expanded,
          selectedPath,
          onSelect,
          onDelete,
        ),
      );
    });
  }

  return rows;
}

export function PlanTree({
  planName,
  treeJson,
  stepCount,
  selectedStepPath,
  onSelectStep,
  onDeleteStep,
  onAddStep,
  onReorder,
}: PlanTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["root"]));

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
  );

  const rows = useMemo(() => {
    if (!treeJson) return [];
    return flattenSteps(
      treeJson,
      "root",
      0,
      expanded,
      selectedStepPath,
      onSelectStep,
      onDeleteStep,
    );
  }, [treeJson, expanded, selectedStepPath, onSelectStep, onDeleteStep]);

  const handleToggle = useCallback(
    (id: string) => {
      setExpanded((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    [],
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const fromPath = String(active.id).replace("node-", "");
    const toPath = String(over.id).replace("node-", "");
    onReorder(fromPath, toPath);
  }

  return (
    <TreeCard
      title={planName || "Plan"}
      badge={`${stepCount} steps`}
      actions={
        <button
          onClick={onAddStep}
          title="Add step"
          className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
        >
          <Plus size={12} />
        </button>
      }
      className="h-full"
    >
      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        {rows.length === 0 ? (
          <p className="py-8 text-center text-[12px] text-muted-foreground">
            Empty plan. Click + to add steps.
          </p>
        ) : (
          rows.map((node) => (
            <SimpleTreeRow
              key={node.id}
              node={node}
              onToggle={() => handleToggle(node.id)}
            />
          ))
        )}
      </DndContext>
    </TreeCard>
  );
}
