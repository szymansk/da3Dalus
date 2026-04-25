"use client";

import { useState, type ReactNode } from "react";
import { useDroppable } from "@dnd-kit/core";
import { Play, Plus, BookTemplate, Pencil, Trash2, FolderOpen, ChevronDown, ChevronRight } from "lucide-react";
import { SimpleTreeRow } from "@/components/workbench/SimpleTreeRow";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import { resolveNodeShapes } from "@/lib/planTreeUtils";
import type { PlanSummary } from "@/hooks/useConstructionPlans";
import type { CreatorInfo } from "@/hooks/useCreators";
import { InlineEditableName } from "./InlineEditableName";

export function renderCreatorTree(
  node: PlanStepNode,
  planId: number,
  level: number,
  expandedSet: Set<string>,
  toggleFn: (key: string) => void,
  onEdit: (planId: number, node: PlanStepNode, path: string) => void,
  creators: CreatorInfo[],
  path: string,
  onAddSuccessor: (planId: number, parentPath: string) => void,
  onDeleteStep: (planId: number, path: string) => void,
): ReactNode {
  const creatorKey = `plan-${planId}-${path}`;
  const isCreatorExpanded = expandedSet.has(creatorKey);
  const { inputs, outputs } = resolveNodeShapes(node, creators);
  const hasChildren = inputs.length > 0 || outputs.length > 0 || (node.successors ?? []).length > 0;

  // Resolve {placeholder} in creator_id for display (e.g. "{wing_index}.vase_wing" → "0.vase_wing")
  const nodeRecord = node as Record<string, unknown>;
  const displayLabel = node.creator_id.replace(/\{(\w+)\}/g, (_match, param) => {
    const val = nodeRecord[param];
    return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
  });

  return (
    <div key={creatorKey} className="flex flex-col">
      <SimpleTreeRow
        node={{
          id: creatorKey,
          label: displayLabel,
          level,
          leaf: !hasChildren,
          expanded: isCreatorExpanded,
          chip: node.$TYPE.replace("Creator", ""),
          onEdit: () => onEdit(planId, node, path),
          editTitle: `Edit ${node.creator_id}`,
          onAdd: () => onAddSuccessor(planId, path),
          addTitle: `Add successor to ${node.creator_id}`,
          onDelete: () => onDeleteStep(planId, path),
        }}
        onToggle={() => toggleFn(creatorKey)}
      />

      {hasChildren && isCreatorExpanded && (
        <>
          {inputs.map((inp) => (
            <SimpleTreeRow
              key={`${creatorKey}-input-${inp.paramName}`}
              node={{
                id: `${creatorKey}-input-${inp.paramName}`,
                label: inp.boundValue
                  ? `\u27A1\uFE0E ${inp.boundValue}`
                  : `\u27A1\uFE0E ${inp.paramName}`,
                level: level + 1,
                leaf: true,
                muted: !!inp.boundValue,
                error: !inp.boundValue,
                annotation: inp.boundValue ? inp.paramName : "unbound",
              }}
              onToggle={() => {}}
            />
          ))}
          {outputs.map((name) => (
            <SimpleTreeRow
              key={`${creatorKey}-output-${name}`}
              node={{
                id: `${creatorKey}-output-${name}`,
                label: `\u2B05\uFE0E ${name}`,
                level: level + 1,
                leaf: true,
                muted: true,
                annotation: "output",
              }}
              onToggle={() => {}}
            />
          ))}
          {(node.successors ?? []).map((successor, index) =>
            renderCreatorTree(
              successor,
              planId,
              level + 1,
              expandedSet,
              toggleFn,
              onEdit,
              creators,
              `${path}.${index}`,
              onAddSuccessor,
              onDeleteStep,
            ),
          )}
        </>
      )}
    </div>
  );
}

interface PlanTreeSectionProps {
  plan: PlanSummary;
  treeJson: PlanStepNode | null;
  creators: CreatorInfo[];
  expanded: boolean;
  onToggle: () => void;
  expandedCreators: Set<string>;
  onToggleCreator: (key: string) => void;
  onEditCreator: (planId: number, node: PlanStepNode, path: string) => void;
  onExecute: (planId: number) => void;
  onSaveAsTemplate: (planId: number) => void;
  onRename: (planId: number, newName: string) => Promise<void> | void;
  onAddStep: (planId: number, parentPath?: string) => void;
  onDeleteStep: (planId: number, path: string) => void;
  onDeletePlan?: (planId: number) => void;
  onShowArtifacts?: (planId: number) => void;
  hidePlanActions?: boolean;
}

export function PlanTreeSection({
  plan,
  treeJson,
  creators,
  expanded,
  onToggle,
  expandedCreators,
  onToggleCreator,
  onEditCreator,
  onExecute,
  onSaveAsTemplate,
  onRename,
  onAddStep,
  onDeleteStep,
  onDeletePlan,
  onShowArtifacts,
  hidePlanActions = false,
}: Readonly<PlanTreeSectionProps>) {
  const [renaming, setRenaming] = useState(false);
  // Plan header is a droppable target for "add to root" drops
  const { setNodeRef: setRootDropRef, isOver: rootIsOver } = useDroppable({
    id: `plan-root-${plan.id}`,
    data: { planId: plan.id, path: "root" },
  });
  return (
    <div className="flex flex-col">
      {/* Plan header row with action buttons */}
      <div
        ref={setRootDropRef}
        className={`group flex items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent ${rootIsOver ? "ring-2 ring-primary" : ""}`}
      >
        <button onClick={onToggle} className="flex items-center">
          {expanded ? (
            <ChevronDown size={12} className="shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight size={12} className="shrink-0 text-muted-foreground" />
          )}
        </button>
        <InlineEditableName
          value={plan.name}
          editing={renaming}
          onCommit={async (newName) => {
            setRenaming(false);
            await onRename(plan.id, newName);
          }}
          onCancel={() => setRenaming(false)}
          className="font-[family-name:var(--font-geist-sans)] text-[13px] font-medium text-foreground"
        />
        {plan.step_count > 0 && !renaming && (
          <span className="text-[11px] text-muted-foreground">({plan.step_count})</span>
        )}
        <span className="flex-1" />
        {!hidePlanActions && (
          <>
            <button
              onClick={() => onExecute(plan.id)}
              title={`Execute ${plan.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Play size={10} />
            </button>
            <button
              onClick={() => onSaveAsTemplate(plan.id)}
              title={`Save ${plan.name} as template`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <BookTemplate size={10} />
            </button>
            {onShowArtifacts && (
              <button
                onClick={() => onShowArtifacts(plan.id)}
                title={`Browse artifacts for ${plan.name}`}
                className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
              >
                <FolderOpen size={10} />
              </button>
            )}
            <button
              onClick={() => setRenaming(true)}
              title={`Rename ${plan.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Pencil size={10} />
            </button>
            {onDeletePlan && (
              <button
                onClick={() => onDeletePlan(plan.id)}
                title={`Delete ${plan.name}`}
                className="hidden size-5 items-center justify-center rounded-lg text-destructive group-hover:flex"
              >
                <Trash2 size={10} />
              </button>
            )}
            <button
              onClick={() => onAddStep(plan.id)}
              title={`Add step to ${plan.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Plus size={10} />
            </button>
          </>
        )}
      </div>

      {/* Creator nodes (when plan is expanded and tree is loaded) */}
      {expanded &&
        treeJson &&
        (treeJson.successors ?? []).map((node, index) =>
          renderCreatorTree(
            node,
            plan.id,
            1,
            expandedCreators,
            onToggleCreator,
            onEditCreator,
            creators,
            `root.${index}`,
            onAddStep,
            onDeleteStep,
          ),
        )}

      {/* Separator between plans (hidden in template mode) */}
      {!hidePlanActions && <div className="mx-2 my-1 border-b border-border/50" />}
    </div>
  );
}
