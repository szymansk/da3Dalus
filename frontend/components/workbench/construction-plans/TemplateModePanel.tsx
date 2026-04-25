"use client";

import React from "react";
import { Play, Pencil, Plus, PanelLeftOpen, PanelLeftClose, ChevronDown } from "lucide-react";
import { TreeCard } from "@/components/workbench/TreeCard";
import { TemplateSelector } from "./TemplateSelector";
import { renderCreatorTree } from "./PlanTreeSection";
import type { MockCreatorNode, MockTemplate } from "./types";

interface TemplateModePanelProps {
  templates: MockTemplate[];
  selectedTemplateId: number | null;
  onSelectTemplate: (id: number) => void;
  expandedCreators: Set<string>;
  onToggleCreator: (key: string) => void;
  onEditCreator: (planId: number, creator: MockCreatorNode) => void;
  treeWide: boolean;
  onToggleWide: () => void;
}

export function TemplateModePanel({
  templates,
  selectedTemplateId,
  onSelectTemplate,
  expandedCreators,
  onToggleCreator,
  onEditCreator,
  treeWide,
  onToggleWide,
}: Readonly<TemplateModePanelProps>) {
  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId) ?? null;

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
          badge={`${selectedTemplate.creators.length} steps`}
          actions={
            <>
              <button
                onClick={() => alert("Play Template: would open aeroplane selector")}
                title="Execute template against an aeroplane"
                className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70"
              >
                <Play size={14} />
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
            <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground font-medium">
              {selectedTemplate.name}
            </span>
            <span className="flex-1" />
            <button
              onClick={() => alert(`Rename: "${selectedTemplate.name}"`)}
              title={`Rename ${selectedTemplate.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Pencil size={10} />
            </button>
            <button
              onClick={() => alert(`Add step to "${selectedTemplate.name}"`)}
              title={`Add step to ${selectedTemplate.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Plus size={10} />
            </button>
          </div>

          {selectedTemplate.creators.map((creator) =>
            renderCreatorTree(
              creator,
              selectedTemplate.id,
              1,
              expandedCreators,
              onToggleCreator,
              onEditCreator,
            ),
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
