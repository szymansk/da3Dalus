"use client";

import type { ReactNode } from "react";
import { Play, Plus, BookTemplate, Pencil, ChevronDown, ChevronRight } from "lucide-react";
import { SimpleTreeRow } from "@/components/workbench/SimpleTreeRow";
import type { MockCreatorNode, MockPlan, MockTemplate } from "./types";

export function renderCreatorTree(
  creator: MockCreatorNode,
  planId: number,
  level: number,
  expandedSet: Set<string>,
  toggleFn: (key: string) => void,
  onEdit: (planId: number, creator: MockCreatorNode) => void,
): ReactNode {
  const creatorKey = `plan-${planId}-${creator.creatorId}`;
  const isCreatorExpanded = expandedSet.has(creatorKey);
  const hasChildren = creator.shapes.length > 0 || (creator.successors ?? []).length > 0;

  return (
    <div key={creatorKey} className="flex flex-col">
      <SimpleTreeRow
        node={{
          id: creatorKey,
          label: creator.creatorId,
          level,
          leaf: !hasChildren,
          expanded: isCreatorExpanded,
          chip: creator.creatorClassName.replace("Creator", ""),
          onEdit: () => onEdit(planId, creator),
          editTitle: `Edit ${creator.creatorId}`,
          onAdd: () => alert(`Add successor to "${creator.creatorId}"`),
          addTitle: `Add successor to ${creator.creatorId}`,
        }}
        onToggle={() => toggleFn(creatorKey)}
      />

      {hasChildren && isCreatorExpanded && (
        <>
          {creator.shapes.map((shape) => (
            <SimpleTreeRow
              key={`${creatorKey}-${shape.direction}-${shape.name}`}
              node={{
                id: `${creatorKey}-${shape.direction}-${shape.name}`,
                label: `${shape.direction === "input" ? "\u2B07" : "\u2B06"} ${shape.name}`,
                level: level + 1,
                leaf: true,
                muted: true,
                annotation: shape.direction,
              }}
              onToggle={() => {}}
            />
          ))}
          {(creator.successors ?? []).map((successor) =>
            renderCreatorTree(successor, planId, level + 1, expandedSet, toggleFn, onEdit),
          )}
        </>
      )}
    </div>
  );
}

interface PlanTreeSectionProps {
  plan: MockPlan | MockTemplate;
  expanded: boolean;
  onToggle: () => void;
  expandedCreators: Set<string>;
  onToggleCreator: (key: string) => void;
  onEditCreator: (planId: number, creator: MockCreatorNode) => void;
  hidePlanActions?: boolean;
}

export function PlanTreeSection({
  plan,
  expanded,
  onToggle,
  expandedCreators,
  onToggleCreator,
  onEditCreator,
  hidePlanActions = false,
}: Readonly<PlanTreeSectionProps>) {
  return (
    <div className="flex flex-col">
      {/* Plan header row with action buttons */}
      <div className="group flex items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent">
        <button onClick={onToggle} className="flex items-center">
          {expanded ? (
            <ChevronDown size={12} className="shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight size={12} className="shrink-0 text-muted-foreground" />
          )}
        </button>
        <span className="font-[family-name:var(--font-geist-sans)] text-[13px] font-medium text-foreground">
          {plan.name}
        </span>
        <span className="flex-1" />
        {!hidePlanActions && (
          <>
            <button
              onClick={() => alert(`Play: would execute "${plan.name}"`)}
              title={`Execute ${plan.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Play size={10} />
            </button>
            <button
              onClick={() => alert(`Save as Template: "${plan.name}"`)}
              title={`Save ${plan.name} as template`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <BookTemplate size={10} />
            </button>
            <button
              onClick={() => alert(`Rename: "${plan.name}"`)}
              title={`Rename ${plan.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Pencil size={10} />
            </button>
            <button
              onClick={() => alert(`Add step to "${plan.name}"`)}
              title={`Add step to ${plan.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Plus size={10} />
            </button>
          </>
        )}
      </div>

      {/* Creator nodes (when plan is expanded) */}
      {expanded &&
        plan.creators.map((creator) =>
          renderCreatorTree(creator, plan.id, 1, expandedCreators, onToggleCreator, onEditCreator),
        )}

      {/* Separator between plans (hidden in template mode) */}
      {!hidePlanActions && <div className="mx-2 my-1 border-b border-border/50" />}
    </div>
  );
}
