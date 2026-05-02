"use client";

import { useState, useCallback, useEffect } from "react";
import {
  DndContext,
  useSensor,
  useSensors,
  PointerSensor,
  type DragEndEvent,
} from "@dnd-kit/core";
import { Hammer, Play, Plus, BookTemplate, PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { useCreators } from "@/hooks/useCreators";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import {
  useAeroplanePlans,
  useConstructionPlans,
  useConstructionPlan,
  createPlan,
  updatePlan,
  deletePlan,
  executePlan,
  toTemplate,
  instantiateTemplate,
  executeStreamUrl,
} from "@/hooks/useConstructionPlans";
import {
  fromBackendTree,
  toBackendTree,
  collectAvailableShapeKeys,
  updateNodeAtPath,
  appendChildAtPath,
  deleteStepAtPath,
  buildStepNode,
} from "@/lib/planTreeUtils";
import { validatePlan } from "@/lib/planValidation";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import { TreeCard } from "@/components/workbench/TreeCard";
import { PlanTreeSection } from "@/components/workbench/construction-plans/PlanTreeSection";
import { TemplateModePanel } from "@/components/workbench/construction-plans/TemplateModePanel";
import { EditParamsModal } from "@/components/workbench/construction-plans/EditParamsModal";
import { AddStepDialog } from "@/components/workbench/construction-plans/AddStepDialog";
import { AeroplanePickerDialog } from "@/components/workbench/construction-plans/AeroplanePickerDialog";
import { ExecutionResultDialog } from "@/components/workbench/construction-plans/ExecutionResultDialog";
import { ArtifactBrowserDialog } from "@/components/workbench/construction-plans/ArtifactBrowserDialog";
import { NewPlanDialog } from "@/components/workbench/construction-plans/NewPlanDialog";
import type { ExecutionResult } from "@/hooks/useConstructionPlans";

// ── Helpers ───────────────────────────────────────────────────────

/** Parse a DnD drop target ID into plan ID and path. */
function parseDropTarget(overId: string): { planId: number; path: string } | null {
  if (overId.startsWith("plan-root-")) {
    return { planId: Number(overId.slice("plan-root-".length)), path: "root" };
  }
  if (overId.startsWith("node-plan-")) {
    const rest = overId.slice("node-plan-".length);
    const dotIdx = rest.indexOf("-");
    if (dotIdx > 0) {
      return { planId: Number(rest.slice(0, dotIdx)), path: rest.slice(dotIdx + 1) };
    }
  }
  return null;
}

/** Toggle a value in a Set, returning a new Set (immutable update). */
function toggleInSet<T>(prev: Set<T>, value: T): Set<T> {
  const next = new Set(prev);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export default function ConstructionPlansPage() {
  const { aeroplaneId, hydrated, openPicker } = useAeroplaneContext();
  const { creators, error: creatorsError } = useCreators();

  // ── Data fetching ─────────────────────────────────────────────
  const { plans, error: plansError, isLoading: plansLoading, mutate: mutatePlans } = useAeroplanePlans(aeroplaneId);
  const { plans: templates, error: templatesError, mutate: mutateTemplates } = useConstructionPlans("template");

  // Full tree for the active plan (expanded plan or plan being edited)
  const [activePlanId, setActivePlanId] = useState<number | null>(null);
  const { plan: activePlanDetail, mutate: mutatePlanDetail } = useConstructionPlan(activePlanId);
  const activeTree = activePlanDetail?.tree_json
    ? fromBackendTree(activePlanDetail.tree_json)
    : null;

  // Full tree for selected template
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const { plan: templateDetail, mutate: mutateTemplateDetail } = useConstructionPlan(selectedTemplateId);
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
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  const [editingNode, setEditingNode] = useState<PlanStepNode | null>(null);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [editingCreatorInfo, setEditingCreatorInfo] = useState<CreatorInfo | null>(null);
  const [editingShapeKeys, setEditingShapeKeys] = useState<string[]>([]);

  // Add-step modal state
  const [addStepOpen, setAddStepOpen] = useState(false);
  const [addStepPlanId, setAddStepPlanId] = useState<number | null>(null);
  const [addStepParentPath, setAddStepParentPath] = useState<string | undefined>(undefined);

  // Execute-template aeroplane picker state
  const [executeTemplateId, setExecuteTemplateId] = useState<number | null>(null);
  const { aeroplanes } = useAeroplanes();

  // Execution result viewer state
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [executionTitle, setExecutionTitle] = useState("");
  const [executionDialogOpen, setExecutionDialogOpen] = useState(false);
  const [executionStreamUrl, setExecutionStreamUrl] = useState<string | null>(null);
  // Plan/template id whose execution is currently displayed in the result
  // dialog. Used to wire the Generated-files section to the right artifact
  // endpoints (gh#339).
  const [executionPlanId, setExecutionPlanId] = useState<number | null>(null);

  // Artifact browser state
  const [artifactsPlanId, setArtifactsPlanId] = useState<number | null>(null);

  // New plan dialog state
  const [newPlanDialogOpen, setNewPlanDialogOpen] = useState(false);

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
      const planName = plans.find((p) => p.id === planId)?.name ?? `Plan ${planId}`;
      // Validate using the active tree if it's the plan being executed
      if (activePlanId === planId && activeTree) {
        const validation = validatePlan(activeTree, creators);
        if (!validation.valid) {
          const summary = validation.issues
            .map((i) => `• ${i.creatorId}: ${i.message}`)
            .join("\n");
          alert(`Validation failed for "${planName}":\n\n${summary}`);
          return;
        }
      }
      setExecutionTitle(`Execute: ${planName}`);
      setExecutionResult(null);
      setExecutionPlanId(planId);
      // Use streaming endpoint — viewer opens immediately, shapes appear incrementally
      setExecutionStreamUrl(executeStreamUrl(aeroplaneId, planId));
      setExecutionDialogOpen(true);
    },
    [aeroplaneId, plans, activePlanId, activeTree, creators],
  );

  const handleSaveAsTemplate = useCallback(
    async (planId: number) => {
      if (!aeroplaneId) return;
      try {
        await toTemplate(aeroplaneId, planId);
        mutateTemplates();
        alert("Saved as template!");
      } catch (err) {
        alert(`Save as template failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [aeroplaneId, mutateTemplates],
  );

  const handleRenamePlan = useCallback(
    async (planId: number, newName: string) => {
      // Need the plan's tree_json to call updatePlan — fetch detail if not loaded
      const isTemplate = templates.some((t) => t.id === planId);
      let detail = null;
      if (isTemplate) {
        detail = templateDetail;
      } else if (activePlanDetail?.id === planId) {
        detail = activePlanDetail;
      }
      if (!detail || detail.id !== planId) {
        alert("Cannot rename: plan data not loaded. Expand the plan first.");
        return;
      }
      try {
        await updatePlan(planId, { name: newName, tree_json: detail.tree_json, plan_type: detail.plan_type, aeroplane_id: detail.aeroplane_id });
        if (isTemplate) mutateTemplates();
        else mutatePlans();
        mutatePlanDetail();
      } catch (err) {
        alert(`Rename failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [templates, activePlanDetail, templateDetail, mutatePlans, mutateTemplates, mutatePlanDetail],
  );

  const handleAddStep = useCallback((planId: number, parentPath?: string) => {
    setAddStepPlanId(planId);
    setAddStepParentPath(parentPath);
    setAddStepOpen(true);
  }, []);

  const handleDeleteStep = useCallback(
    async (planId: number, path: string) => {
      const isTemplate = templates.some((t) => t.id === planId);
      const tree = isTemplate ? templateTree : activeTree;
      const detail = isTemplate ? templateDetail : activePlanDetail;
      if (!tree || !detail) {
        alert("Plan data not loaded.");
        return;
      }
      const updatedTree = deleteStepAtPath(tree, path);
      try {
        await updatePlan(planId, { name: detail.name, tree_json: toBackendTree(updatedTree), plan_type: detail.plan_type, aeroplane_id: detail.aeroplane_id });
        if (isTemplate) { mutateTemplates(); mutateTemplateDetail(); }
        else { mutatePlans(); mutatePlanDetail(); }
      } catch (err) {
        alert(`Delete step failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [templates, templateTree, activeTree, templateDetail, activePlanDetail, mutatePlans, mutateTemplates, mutatePlanDetail, mutateTemplateDetail],
  );

  const handleDeleteTemplate = useCallback(
    async (templateId: number) => {
      if (!confirm("Delete this template? This cannot be undone.")) return;
      try {
        await deletePlan(templateId);
        mutateTemplates();
        if (selectedTemplateId === templateId) setSelectedTemplateId(null);
      } catch (err) {
        alert(`Delete template failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [mutateTemplates, selectedTemplateId],
  );

  const handleDeletePlan = useCallback(
    async (planId: number) => {
      if (!confirm("Delete this plan? This cannot be undone.")) return;
      try {
        await deletePlan(planId);
        mutatePlans();
        if (activePlanId === planId) setActivePlanId(null);
      } catch (err) {
        alert(`Delete plan failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [mutatePlans, activePlanId],
  );

  /** Shared helper: add a creator as a child node at a given path in a plan/template tree. */
  const addCreatorToPlan = useCallback(
    async (planId: number, parentPath: string, creator: CreatorInfo) => {
      const isTemplate = templates.some((t) => t.id === planId);
      const tree = isTemplate ? templateTree : activeTree;
      const detail = isTemplate ? templateDetail : activePlanDetail;
      if (!tree || !detail) {
        throw new Error("Plan data not loaded. Expand the plan first.");
      }
      const newNode = buildStepNode(creator, tree);
      const updatedTree = appendChildAtPath(tree, parentPath, newNode);
      await updatePlan(planId, { name: detail.name, tree_json: toBackendTree(updatedTree), plan_type: detail.plan_type, aeroplane_id: detail.aeroplane_id });
      if (isTemplate) { mutateTemplates(); mutateTemplateDetail(); }
      else { mutatePlans(); mutatePlanDetail(); }
    },
    [templates, templateTree, activeTree, templateDetail, activePlanDetail, mutatePlans, mutateTemplates, mutatePlanDetail, mutateTemplateDetail],
  );

  const handleAddStepSelect = useCallback(
    async (creator: CreatorInfo) => {
      if (addStepPlanId == null) return;
      await addCreatorToPlan(addStepPlanId, addStepParentPath ?? "root", creator);
    },
    [addStepPlanId, addStepParentPath, addCreatorToPlan],
  );

  const handleEditCreator = useCallback(
    (planId: number, node: PlanStepNode, path: string) => {
      const info = creators.find((c) => c.class_name === node.$TYPE) ?? null;
      // Use the plan tree if editing a plan, template tree if editing a template
      const isTemplate = templates.some((t) => t.id === planId);
      const tree = isTemplate ? templateTree : activeTree;
      const shapeKeys = tree ? collectAvailableShapeKeys(tree, creators, path) : [];
      setEditingPlanId(planId);
      setEditingNode(node);
      setEditingPath(path);
      setEditingCreatorInfo(info);
      setEditingShapeKeys(shapeKeys);
      setEditModalOpen(true);
      // Ensure the correct plan detail is loaded for saving
      if (!isTemplate) setActivePlanId(planId);
    },
    [creators, templates, activeTree, templateTree],
  );

  const handleEditSave = useCallback(
    async (path: string, params: Record<string, unknown>): Promise<void> => {
      if (!editingPlanId || !editingNode) {
        throw new Error("Cannot save: no plan or node selected.");
      }
      // Determine which tree we're editing (plan or template)
      const isTemplate = templates.some((t) => t.id === editingPlanId);
      const tree = isTemplate ? templateTree : activeTree;
      const detail = isTemplate ? templateDetail : activePlanDetail;
      if (!tree || !detail) {
        throw new Error("Cannot save: plan data is not loaded. Please close and try again.");
      }
      const updatedNode = { ...editingNode, ...params } as PlanStepNode;
      const updatedTree = updateNodeAtPath(tree, path, updatedNode);
      const backendTree = toBackendTree(updatedTree);
      await updatePlan(editingPlanId, {
        name: detail.name,
        tree_json: backendTree,
        plan_type: detail.plan_type,
        aeroplane_id: detail.aeroplane_id,
      });
      if (isTemplate) { mutateTemplates(); mutateTemplateDetail(); }
      else { mutatePlans(); mutatePlanDetail(); }
    },
    [editingPlanId, editingNode, templates, templateTree, activeTree, templateDetail, activePlanDetail, mutatePlanDetail, mutateTemplateDetail, mutatePlans, mutateTemplates],
  );

  const handleCreateEmptyPlan = useCallback(async () => {
    if (!aeroplaneId) return;
    const newPlan = await createPlan({
      name: `New Plan ${plans.length + 1}`,
      tree_json: { $TYPE: "ConstructionRootNode", creator_id: "root", successors: {} },
      plan_type: "plan",
      aeroplane_id: aeroplaneId,
    });
    mutatePlans();
    setExpandedPlans((prev) => new Set(prev).add(newPlan.id));
    setActivePlanId(newPlan.id);
  }, [aeroplaneId, plans.length, mutatePlans]);

  const handleCreateFromTemplate = useCallback(async (templateId: number) => {
    if (!aeroplaneId) return;
    const newPlan = await instantiateTemplate(aeroplaneId, templateId);
    mutatePlans();
    setExpandedPlans((prev) => new Set(prev).add(newPlan.id));
    setActivePlanId(newPlan.id);
  }, [aeroplaneId, mutatePlans]);

  // ── Template callbacks ────────────────────────────────────────

  const handleSelectTemplate = useCallback((id: number) => {
    setSelectedTemplateId(id);
  }, []);

  const handleExecuteTemplate = useCallback((templateId: number) => {
    setExecuteTemplateId(templateId);
  }, []);

  const handleExecuteTemplateOnAeroplane = useCallback(
    async (selectedAeroplaneId: string) => {
      if (executeTemplateId == null) return;
      const tpl = templates.find((t) => t.id === executeTemplateId);
      const aero = aeroplanes.find((a) => a.id === selectedAeroplaneId);
      // Validate using the loaded template tree
      if (selectedTemplateId === executeTemplateId && templateTree) {
        const validation = validatePlan(templateTree, creators);
        if (!validation.valid) {
          const summary = validation.issues
            .map((i) => `• ${i.creatorId}: ${i.message}`)
            .join("\n");
          alert(`Validation failed for template "${tpl?.name ?? "template"}":\n\n${summary}`);
          setExecuteTemplateId(null);
          return;
        }
      }
      setExecutionTitle(`Execute: ${tpl?.name ?? "template"} on ${aero?.name ?? "aeroplane"}`);
      setExecutionResult(null);
      setExecutionPlanId(executeTemplateId);
      setExecutionDialogOpen(true);
      setExecuteTemplateId(null);
      try {
        const result = await executePlan(selectedAeroplaneId, executeTemplateId);
        setExecutionResult(result);
      } catch (err) {
        setExecutionResult({
          status: "error",
          shape_keys: [],
          export_paths: [],
          error: err instanceof Error ? err.message : String(err),
          duration_ms: 0,
          tessellation: null,
          artifact_dir: null,
          execution_id: null,
        });
      }
    },
    [executeTemplateId, templates, aeroplanes, selectedTemplateId, templateTree, creators],
  );

  // ── Drag-and-drop ─────────────────────────────────────────────

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over) return;
      const activeId = String(active.id);
      if (!activeId.startsWith("creator-")) return;

      const creator = active.data.current?.creator as CreatorInfo | undefined;
      if (!creator) return;

      const target = parseDropTarget(String(over.id));
      if (!target) return;

      try {
        await addCreatorToPlan(target.planId, target.path, creator);
      } catch (err) {
        alert(`Drop failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    },
    [addCreatorToPlan],
  );

  // ── No-aeroplane guard ────────────────────────────────────────

  useEffect(() => {
    if (hydrated && !aeroplaneId) openPicker();
  }, [hydrated, aeroplaneId, openPicker]);

  if (!aeroplaneId) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="text-[13px] text-muted-foreground">No aeroplane selected</span>
      </div>
    );
  }

  // ── Loading / error states ─────────────────────────────────────
  const fetchError = plansError || templatesError || creatorsError;
  if (plansLoading && plans.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-[13px] text-muted-foreground">Loading construction plans...</p>
      </div>
    );
  }
  if (fetchError) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <p className="text-[13px] text-destructive">
            Failed to load construction plans.
          </p>
          <button
            onClick={() => { mutatePlans(); mutateTemplates(); }}
            className="rounded-full border border-border px-4 py-2 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Retry
          </button>
        </div>
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
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
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
                      onClick={() => setNewPlanDialogOpen(true)}
                      title="Create new plan"
                      className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                    >
                      <Plus size={12} />
                    </button>
                    <button
                      onClick={async () => {
                        if (!aeroplaneId || plans.length === 0) return;
                        setExecutionTitle(`Execute all plans (${plans.length})`);
                        setExecutionResult(null);
                        setExecutionPlanId(null);
                        setExecutionDialogOpen(true);
                        try {
                          // Execute sequentially; show result of last successful execution
                          let lastResult: ExecutionResult | null = null;
                          let lastPlanId: number | null = null;
                          for (const p of plans) {
                            lastResult = await executePlan(aeroplaneId, p.id);
                            lastPlanId = p.id;
                            if (lastResult.status === "error") break;
                          }
                          setExecutionResult(lastResult);
                          setExecutionPlanId(lastPlanId);
                        } catch (err) {
                          setExecutionResult({
                            status: "error",
                            shape_keys: [],
                            export_paths: [],
                            error: err instanceof Error ? err.message : String(err),
                            duration_ms: 0,
                            tessellation: null,
                            artifact_dir: null,
                            execution_id: null,
                          });
                        }
                      }}
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
                    onDeleteStep={handleDeleteStep}
                    onDeletePlan={handleDeletePlan}
                    onShowArtifacts={(id) => setArtifactsPlanId(id)}
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
                onRenameTemplate={handleRenamePlan}
                onAddStep={handleAddStep}
                onDeleteStep={handleDeleteStep}
                onDeleteTemplate={handleDeleteTemplate}
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
            draggable
            onSelect={(creator) =>
              alert(`Drag "${creator.class_name}" onto a plan tree, or use a plan's + button.`)
            }
          />
        </div>
      </div>
    </DndContext>

      <EditParamsModal
        open={editModalOpen}
        node={editingNode}
        nodePath={editingPath}
        creatorInfo={editingCreatorInfo}
        availableShapeKeys={editingShapeKeys}
        onClose={() => {
          setEditModalOpen(false);
          setEditingPlanId(null);
          setEditingNode(null);
          setEditingPath(null);
        }}
        onSave={handleEditSave}
      />

      <AddStepDialog
        open={addStepOpen}
        creators={creators}
        parentLabel={
          addStepPlanId
            ? plans.find((p) => p.id === addStepPlanId)?.name ??
              templates.find((t) => t.id === addStepPlanId)?.name ??
              "plan"
            : "plan"
        }
        onClose={() => {
          setAddStepOpen(false);
          setAddStepPlanId(null);
          setAddStepParentPath(undefined);
        }}
        onSelect={handleAddStepSelect}
      />

      <AeroplanePickerDialog
        open={executeTemplateId != null}
        aeroplanes={aeroplanes}
        title="Select aeroplane to execute against"
        onClose={() => setExecuteTemplateId(null)}
        onSelect={handleExecuteTemplateOnAeroplane}
      />

      <ExecutionResultDialog
        open={executionDialogOpen}
        title={executionTitle}
        result={executionResult}
        streamUrl={executionStreamUrl}
        planId={executionPlanId}
        onClose={() => {
          setExecutionDialogOpen(false);
          setExecutionResult(null);
          setExecutionStreamUrl(null);
          setExecutionPlanId(null);
        }}
      />

      <NewPlanDialog
        open={newPlanDialogOpen}
        templates={templates}
        onClose={() => setNewPlanDialogOpen(false)}
        onCreateEmpty={handleCreateEmptyPlan}
        onCreateFromTemplate={handleCreateFromTemplate}
      />

      <ArtifactBrowserDialog
        open={artifactsPlanId != null}
        planId={artifactsPlanId}
        planName={
          artifactsPlanId
            ? plans.find((p) => p.id === artifactsPlanId)?.name ?? "plan"
            : "plan"
        }
        onClose={() => setArtifactsPlanId(null)}
      />
    </>
  );
}
