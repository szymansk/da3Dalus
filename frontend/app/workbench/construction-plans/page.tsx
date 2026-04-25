"use client";

import { useState, useCallback, useEffect } from "react";
import { Hammer, Play, BookTemplate, PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { useCreators } from "@/hooks/useCreators";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import {
  useAeroplanePlans,
  useConstructionPlans,
  useConstructionPlan,
  updatePlan,
  executePlan,
  toTemplate,
} from "@/hooks/useConstructionPlans";
import {
  fromBackendTree,
  toBackendTree,
  collectAvailableShapeKeys,
  updateNodeAtPath,
} from "@/lib/planTreeUtils";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import { TreeCard } from "@/components/workbench/TreeCard";
import { PlanTreeSection } from "@/components/workbench/construction-plans/PlanTreeSection";
import { TemplateModePanel } from "@/components/workbench/construction-plans/TemplateModePanel";
import { EditParamsModal } from "@/components/workbench/construction-plans/EditParamsModal";

// ── Helpers ───────────────────────────────────────────────────────

/** Toggle a value in a Set, returning a new Set (immutable update). */
function toggleInSet<T>(prev: Set<T>, value: T): Set<T> {
  const next = new Set(prev);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export default function ConstructionPlansPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const { creators } = useCreators();

  // ── Data fetching ─────────────────────────────────────────────
  const { plans, mutate: mutatePlans } = useAeroplanePlans(aeroplaneId);
  const { plans: templates, mutate: mutateTemplates } = useConstructionPlans("template");

  // Full tree for the active plan (expanded plan or plan being edited)
  const [activePlanId, setActivePlanId] = useState<number | null>(null);
  const { plan: activePlanDetail, mutate: mutatePlanDetail } = useConstructionPlan(activePlanId);
  const activeTree = activePlanDetail?.tree_json
    ? fromBackendTree(activePlanDetail.tree_json)
    : null;

  // Full tree for selected template
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const { plan: templateDetail } = useConstructionPlan(selectedTemplateId);
  const templateTree = templateDetail?.tree_json
    ? fromBackendTree(templateDetail.tree_json)
    : null;

  // ── View state ────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<"plans" | "templates">("plans");
  const [treeWide, setTreeWide] = useState(false);

  // Plan mode state
  const [expandedPlans, setExpandedPlans] = useState<Set<number>>(new Set());
  const [expandedCreators, setExpandedCreators] = useState<Set<string>>(new Set());

  // Template mode state
  const [templateExpandedCreators, setTemplateExpandedCreators] = useState<Set<string>>(new Set());

  // Edit modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<PlanStepNode | null>(null);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [editingCreatorInfo, setEditingCreatorInfo] = useState<CreatorInfo | null>(null);
  const [editingShapeKeys, setEditingShapeKeys] = useState<string[]>([]);

  // ── Auto-expand first plan on load ────────────────────────────
  useEffect(() => {
    if (plans.length > 0 && expandedPlans.size === 0) {
      const firstId = plans[0].id;
      setExpandedPlans(new Set([firstId]));
      setActivePlanId(firstId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plans]);

  // ── Callbacks ─────────────────────────────────────────────────

  const togglePlan = useCallback((planId: number) => {
    setExpandedPlans((prev) => {
      const next = new Set(prev);
      if (next.has(planId)) {
        next.delete(planId);
      } else {
        next.add(planId);
        setActivePlanId(planId);
      }
      return next;
    });
  }, []);

  const toggleCreator = useCallback(
    (key: string) => setExpandedCreators((prev) => toggleInSet(prev, key)),
    [],
  );

  const toggleTemplateCreator = useCallback(
    (key: string) => setTemplateExpandedCreators((prev) => toggleInSet(prev, key)),
    [],
  );

  const handleExecutePlan = useCallback(
    async (planId: number) => {
      if (!aeroplaneId) return;
      try {
        const result = await executePlan(aeroplaneId, planId);
        if (result.status === "error") {
          alert(`Execution failed: ${result.error}`);
        } else {
          alert(
            `Execution succeeded! ${result.shape_keys?.length ?? 0} shapes produced in ${result.duration_ms}ms`,
          );
          // TODO: Open 3D viewer with result.tessellation
        }
      } catch (err) {
        alert(`Execution error: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [aeroplaneId],
  );

  const handleSaveAsTemplate = useCallback(
    async (planId: number) => {
      if (!aeroplaneId) return;
      try {
        await toTemplate(aeroplaneId, planId);
        mutateTemplates();
        alert("Saved as template!");
      } catch (err) {
        alert(`Error: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [aeroplaneId, mutateTemplates],
  );

  const handleRenamePlan = useCallback(async (planId: number, newName: string) => {
    // For now, alert stub — inline rename UI comes later
    alert(`Rename plan ${planId} to "${newName}"`);
  }, []);

  const handleAddStep = useCallback(async (planId: number, parentPath?: string) => {
    // For now, alert stub — creator picker integration comes later
    alert(`Add step to plan ${planId}${parentPath ? ` at ${parentPath}` : ""}`);
  }, []);

  const handleEditCreator = useCallback(
    (planId: number, node: PlanStepNode, path: string) => {
      const info = creators.find((c) => c.class_name === node.$TYPE) ?? null;
      const tree = activePlanId === planId ? activeTree : templateTree;
      const shapeKeys = tree ? collectAvailableShapeKeys(tree, creators, path) : [];
      setEditingNode(node);
      setEditingPath(path);
      setEditingCreatorInfo(info);
      setEditingShapeKeys(shapeKeys);
      setEditModalOpen(true);
      setActivePlanId(planId);
    },
    [creators, activePlanId, activeTree, templateTree],
  );

  const handleEditSave = useCallback(
    async (path: string, params: Record<string, unknown>) => {
      if (!activePlanId || !activeTree || !activePlanDetail) return;
      const updatedNode = { ...editingNode!, ...params } as PlanStepNode;
      const updatedTree = updateNodeAtPath(activeTree, path, updatedNode);
      const backendTree = toBackendTree(updatedTree);
      try {
        await updatePlan(activePlanId, {
          name: activePlanDetail.name,
          tree_json: backendTree,
        });
        mutatePlanDetail();
        mutatePlans();
      } catch (err) {
        alert(`Save failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [activePlanId, activeTree, activePlanDetail, editingNode, mutatePlanDetail, mutatePlans],
  );

  // ── Template callbacks ────────────────────────────────────────

  const handleSelectTemplate = useCallback((id: number) => {
    setSelectedTemplateId(id);
  }, []);

  const handleExecuteTemplate = useCallback(
    async (templateId: number) => {
      // Alert stub — needs aeroplane picker dialog
      alert(`Execute template ${templateId}: not yet implemented (needs aeroplane picker)`);
    },
    [],
  );

  const handleRenameTemplate = useCallback(async (templateId: number, name: string) => {
    // Alert stub
    alert(`Rename template ${templateId} to "${name}"`);
  }, []);

  const handleAddStepToTemplate = useCallback(async (templateId: number, parentPath?: string) => {
    // Alert stub
    alert(`Add step to template ${templateId}${parentPath ? ` at ${parentPath}` : ""}`);
  }, []);

  // ── No-aeroplane guard ────────────────────────────────────────

  if (!aeroplaneId) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-[13px] text-muted-foreground">
          Select an aeroplane to view its construction plans.
        </p>
      </div>
    );
  }

  // ── Derived values ──────────────────────────────────────────────
  const totalSteps = plans.reduce((s, p) => s + p.step_count, 0);
  const panelStyle = { width: treeWide ? "66%" : 360, minWidth: treeWide ? "66%" : 360 };

  function ModeButton({
    mode,
    Icon,
    label,
  }: Readonly<{ mode: "plans" | "templates"; Icon: typeof Hammer; label: string }>) {
    return (
      <button
        onClick={() => setViewMode(mode)}
        className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
          viewMode === mode
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Icon size={12} /> {label}
      </button>
    );
  }

  function WidthToggle() {
    return (
      <button
        onClick={() => setTreeWide((w) => !w)}
        title={treeWide ? "Collapse tree panel" : "Expand tree panel"}
        className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent"
      >
        {treeWide ? <PanelLeftClose size={12} /> : <PanelLeftOpen size={12} />}
      </button>
    );
  }

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
        {/* Left panel */}
        <div
          className="flex min-h-0 shrink-0 flex-col overflow-hidden transition-all duration-300"
          style={panelStyle}
        >
          <div className="flex h-full flex-col gap-3 overflow-hidden">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
                <ModeButton mode="plans" Icon={Hammer} label="Plans" />
                <ModeButton mode="templates" Icon={BookTemplate} label="Templates" />
              </div>
            </div>

            {viewMode === "plans" && (
              <TreeCard
                title="Construction Plans"
                badge={`${totalSteps} steps`}
                actions={
                  <>
                    <button
                      onClick={() => alert("Execute All: would execute all plans")}
                      title="Execute all plans"
                      className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70"
                    >
                      <Play size={14} />
                    </button>
                    <WidthToggle />
                  </>
                }
              >
                {plans.map((plan) => (
                  <PlanTreeSection
                    key={plan.id}
                    plan={plan}
                    treeJson={activePlanId === plan.id ? activeTree : null}
                    creators={creators}
                    expanded={expandedPlans.has(plan.id)}
                    onToggle={() => togglePlan(plan.id)}
                    expandedCreators={expandedCreators}
                    onToggleCreator={toggleCreator}
                    onEditCreator={handleEditCreator}
                    onExecute={handleExecutePlan}
                    onSaveAsTemplate={handleSaveAsTemplate}
                    onRename={handleRenamePlan}
                    onAddStep={handleAddStep}
                  />
                ))}
              </TreeCard>
            )}

            {viewMode === "templates" && (
              <TemplateModePanel
                templates={templates}
                selectedTemplateId={selectedTemplateId}
                selectedTemplateTree={templateTree}
                creators={creators}
                onSelectTemplate={handleSelectTemplate}
                expandedCreators={templateExpandedCreators}
                onToggleCreator={toggleTemplateCreator}
                onEditCreator={handleEditCreator}
                onExecuteTemplate={handleExecuteTemplate}
                onRenameTemplate={handleRenameTemplate}
                onAddStep={handleAddStepToTemplate}
                treeWide={treeWide}
                onToggleWide={() => setTreeWide((w) => !w)}
              />
            )}
          </div>
        </div>

        {/* Right panel: Creator Gallery */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2.5">
            <Hammer className="size-5 text-primary" />
            <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
              Creator Catalog
            </h1>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              {creators.length} creators
            </span>
          </div>
          <CreatorGallery
            creators={creators}
            onSelect={(creator) =>
              alert(`Would add "${creator.class_name}" to plan via drag-and-drop`)
            }
          />
        </div>
      </div>

      <EditParamsModal
        open={editModalOpen}
        node={editingNode}
        nodePath={editingPath}
        creatorInfo={editingCreatorInfo}
        availableShapeKeys={editingShapeKeys}
        onClose={() => {
          setEditModalOpen(false);
          setEditingNode(null);
          setEditingPath(null);
        }}
        onSave={handleEditSave}
      />
    </>
  );
}
