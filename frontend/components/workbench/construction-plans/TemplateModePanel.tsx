"use client";

import { useState } from "react";
import { Play, Pencil, Plus, Trash2, PanelLeftOpen, PanelLeftClose, ChevronDown } from "lucide-react";
import { TreeCard } from "@/components/workbench/TreeCard";
import { TemplateSelector } from "./TemplateSelector";
import { renderCreatorTree } from "./PlanTreeSection";
import { InlineEditableName } from "./InlineEditableName";
import type { PlanSummary } from "@/hooks/useConstructionPlans";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";

interface TemplateModePanelProps {
  templates: PlanSummary[];
  selectedTemplateId: number | null;
  selectedTemplateTree: PlanStepNode | null;
  creators: CreatorInfo[];
  onSelectTemplate: (id: number) => void;
  expandedCreators: Set<string>;
  onToggleCreator: (key: string) => void;
  onEditCreator: (planId: number, node: PlanStepNode, path: string) => void;
  onExecuteTemplate: (templateId: number) => void;
  onRenameTemplate: (templateId: number, newName: string) => Promise<void> | void;
  onAddStep: (templateId: number, parentPath?: string) => void;
  onDeleteStep: (planId: number, path: string) => void;
  onDeleteTemplate: (templateId: number) => void;
  treeWide: boolean;
  onToggleWide: () => void;
}

export function TemplateModePanel({
  templates,
  selectedTemplateId,
  selectedTemplateTree,
  creators,
  onSelectTemplate,
  expandedCreators,
  onToggleCreator,
  onEditCreator,
  onExecuteTemplate,
  onRenameTemplate,
  onAddStep,
  onDeleteStep,
  onDeleteTemplate,
  treeWide,
  onToggleWide,
}: Readonly<TemplateModePanelProps>) {
  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId) ?? null;
  const [renaming, setRenaming] = useState(false);

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden">
      <TemplateSelector
        templates={templates}
        selectedId={selectedTemplateId}
        onSelect={onSelectTemplate}
      />

      {selectedTemplate ? (
        <TreeCard
          title={selectedTemplate.name}
          badge={`${selectedTemplate.step_count} steps`}
          actions={
            <>
              <button
                onClick={() => onExecuteTemplate(selectedTemplate.id)}
                title="Execute template against an aeroplane"
                className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70"
              >
                <Play size={14} />
              </button>
              <button
                onClick={() => onDeleteTemplate(selectedTemplate.id)}
                title={`Delete ${selectedTemplate.name}`}
                className="flex size-6 items-center justify-center rounded-lg text-destructive hover:text-destructive/70"
              >
                <Trash2 size={14} />
              </button>
              <button
                onClick={onToggleWide}
                title={treeWide ? "Collapse tree panel" : "Expand tree panel"}
                className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent"
              >
                {treeWide ? <PanelLeftClose size={12} /> : <PanelLeftOpen size={12} />}
              </button>
            </>
          }
        >
          {/* Template root node */}
          <div className="group flex items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent">
            <ChevronDown size={12} className="shrink-0 text-muted-foreground" />
            <InlineEditableName
              value={selectedTemplate.name}
              editing={renaming}
              onCommit={async (newName) => {
                setRenaming(false);
                await onRenameTemplate(selectedTemplate.id, newName);
              }}
              onCancel={() => setRenaming(false)}
              className="font-[family-name:var(--font-geist-sans)] text-[13px] font-medium text-foreground"
            />
            <span className="flex-1" />
            <button
              onClick={() => setRenaming(true)}
              title={`Rename ${selectedTemplate.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Pencil size={10} />
            </button>
            <button
              onClick={() => onAddStep(selectedTemplate.id)}
              title={`Add step to ${selectedTemplate.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Plus size={10} />
            </button>
          </div>

          {selectedTemplateTree == null ? (
            <div className="flex items-center justify-center py-4">
              <p className="text-[12px] text-muted-foreground">Loading steps…</p>
            </div>
          ) : (
            (selectedTemplateTree.successors ?? []).map((node, i) =>
              renderCreatorTree(
                node,
                selectedTemplate.id,
                1,
                expandedCreators,
                onToggleCreator,
                onEditCreator,
                creators,
                `root.${i}`,
                onAddStep,
                onDeleteStep,
              ),
            )
          )}
        </TreeCard>
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-[13px] text-muted-foreground">
            Select a template from the dropdown above
          </p>
        </div>
      )}
    </div>
  );
}
