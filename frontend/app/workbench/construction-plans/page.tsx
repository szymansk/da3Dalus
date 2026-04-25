"use client";

import { useState, useCallback } from "react";
import {
  Hammer,
  Play,
  BookTemplate,
  PanelLeftOpen,
  PanelLeftClose,
} from "lucide-react";
import { useCreators } from "@/hooks/useCreators";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import { TreeCard } from "@/components/workbench/TreeCard";
import {
  MOCK_PLANS,
  MOCK_TEMPLATES,
  countCreators,
  type MockCreatorNode,
} from "@/components/workbench/construction-plans/types";
import { PlanTreeSection } from "@/components/workbench/construction-plans/PlanTreeSection";
import { TemplateModePanel } from "@/components/workbench/construction-plans/TemplateModePanel";
import { EditParamsModal } from "@/components/workbench/construction-plans/EditParamsModal";

// ── Initial expanded keys (click-dummy defaults) ──────────────────
const INITIAL_EXPANDED_CREATORS = new Set([
  "plan-1-vase_wing", "plan-1-mirror_wing",
  "plan-4-raw_wing", "plan-4-positioned_wing",
  "plan-4-servo_cutout_left", "plan-4-servo_cutout_right",
  "plan-4-wing_shell", "plan-4-wing_with_servos", "plan-4-wing_repaired",
  "plan-4-wing_step_export", "plan-4-wing_stl_export", "plan-4-wing_3mf_export",
  "plan-4-print_orientation", "plan-4-print_stl_export",
  "plan-4-wing_loft", "plan-4-servo_left", "plan-4-servo_right", "plan-4-spar_carbon_tube",
  "plan-5-depth_01_wing", "plan-5-depth_02_transform", "plan-5-depth_03_cut",
  "plan-5-depth_04_offset", "plan-5-depth_05_fuse", "plan-5-depth_06_repair",
  "plan-5-depth_07_reposition", "plan-5-depth_08_intersect", "plan-5-depth_09_compound",
  "plan-5-depth_10_export",
]);

export default function ConstructionPlansPage() {
  const { creators } = useCreators();

  // View mode
  const [viewMode, setViewMode] = useState<"plans" | "templates">("plans");
  const [treeWide, setTreeWide] = useState(false);

  // Plan mode state
  const [expandedPlans, setExpandedPlans] = useState<Set<number>>(new Set([1, 4, 5]));
  const [expandedCreators, setExpandedCreators] = useState<Set<string>>(INITIAL_EXPANDED_CREATORS);

  // Template mode state
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [templateExpandedCreators, setTemplateExpandedCreators] = useState<Set<string>>(new Set());

  // Edit modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingCreator, setEditingCreator] = useState<MockCreatorNode | null>(null);

  // ── Callbacks ───────────────────────────────────────────────────

  const togglePlan = useCallback((planId: number) => {
    setExpandedPlans((prev) => {
      const next = new Set(prev);
      if (next.has(planId)) next.delete(planId);
      else next.add(planId);
      return next;
    });
  }, []);

  const toggleCreator = useCallback((key: string) => {
    setExpandedCreators((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleTemplateCreator = useCallback((key: string) => {
    setTemplateExpandedCreators((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const handleEditCreator = useCallback((_planId: number, creator: MockCreatorNode) => {
    setEditingCreator(creator);
    setEditModalOpen(true);
  }, []);

  const handleSelectTemplate = useCallback((id: number) => {
    setSelectedTemplateId(id);
    const template = MOCK_TEMPLATES.find((t) => t.id === id);
    if (template) {
      setTemplateExpandedCreators(
        new Set(template.creators.map((c) => `plan-${id}-${c.creatorId}`)),
      );
    }
  }, []);

  // ── Derived values ──────────────────────────────────────────────
  const editingCreatorInfo = editingCreator
    ? creators.find((c) => c.class_name === editingCreator.creatorClassName) ?? null
    : null;
  const totalSteps = MOCK_PLANS.reduce((sum, p) => sum + countCreators(p.creators), 0);

  const modeBtn = (mode: "plans" | "templates", Icon: typeof Hammer, label: string) => (
    <button
      onClick={() => setViewMode(mode)}
      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
        viewMode === mode ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      <Icon size={12} /> {label}
    </button>
  );

  const widthToggle = (
    <button
      onClick={() => setTreeWide((w) => !w)}
      title={treeWide ? "Collapse tree panel" : "Expand tree panel"}
      className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent"
    >
      {treeWide ? <PanelLeftClose size={12} /> : <PanelLeftOpen size={12} />}
    </button>
  );

  const panelStyle = { width: treeWide ? "66%" : 360, minWidth: treeWide ? "66%" : 360 };

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
        {/* Left panel */}
        <div className="flex min-h-0 shrink-0 flex-col overflow-hidden transition-all duration-300" style={panelStyle}>
          <div className="flex h-full flex-col gap-3 overflow-hidden">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
                {modeBtn("plans", Hammer, "Plans")}
                {modeBtn("templates", BookTemplate, "Templates")}
              </div>
            </div>

            {viewMode === "plans" && (
              <TreeCard title="Construction Plans" badge={`${totalSteps} steps`} actions={<>
                <button onClick={() => alert("Execute All: would execute all plans")} title="Execute all plans"
                  className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70">
                  <Play size={14} />
                </button>
                {widthToggle}
              </>}>
                {MOCK_PLANS.map((plan) => (
                  <PlanTreeSection key={plan.id} plan={plan} expanded={expandedPlans.has(plan.id)}
                    onToggle={() => togglePlan(plan.id)} expandedCreators={expandedCreators}
                    onToggleCreator={toggleCreator} onEditCreator={handleEditCreator} />
                ))}
              </TreeCard>
            )}

            {viewMode === "templates" && (
              <TemplateModePanel templates={MOCK_TEMPLATES} selectedTemplateId={selectedTemplateId}
                onSelectTemplate={handleSelectTemplate} expandedCreators={templateExpandedCreators}
                onToggleCreator={toggleTemplateCreator} onEditCreator={handleEditCreator}
                treeWide={treeWide} onToggleWide={() => setTreeWide((w) => !w)} />
            )}
          </div>
        </div>

        {/* Right panel: Creator Gallery */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2.5">
            <Hammer className="size-5 text-primary" />
            <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">Creator Catalog</h1>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">{creators.length} creators</span>
          </div>
          <CreatorGallery creators={creators}
            onSelect={(creator) => alert(`Would add "${creator.class_name}" to plan via drag-and-drop`)} />
        </div>
      </div>

      <EditParamsModal key={editingCreator?.creatorId} open={editModalOpen} creator={editingCreator}
        creatorInfo={editingCreatorInfo} onClose={() => { setEditModalOpen(false); setEditingCreator(null); }} />
    </>
  );
}
