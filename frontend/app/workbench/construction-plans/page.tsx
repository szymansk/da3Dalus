"use client";

import { useState, useCallback, useRef } from "react";
import { Hammer, Plus, Trash2, Play, Loader2, BookTemplate, Copy, X, Maximize2, Minimize2 } from "lucide-react";
import { CadViewer } from "@/components/workbench/CadViewer";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { PlanTree, type PlanStepNode } from "@/components/workbench/PlanTree";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import { CreatorParameterForm } from "@/components/workbench/CreatorParameterForm";
import { CreatorDetailView } from "@/components/workbench/CreatorDetailView";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import {
  useConstructionPlans,
  useConstructionPlan,
  useAeroplanePlans,
  createPlan,
  updatePlan,
  deletePlan,
  executePlan,
  instantiateTemplate,
  toTemplate,
  type ExecutionResult,
} from "@/hooks/useConstructionPlans";
import { useCreators, type CreatorInfo } from "@/hooks/useCreators";
import {
  getStepAtPath,
  deleteStepAtPath,
  insertStepAtPath,
  updateNodeAtPath,
  collectAvailableShapeKeys,
  resolveIdTemplate,
  computeReorderTargetPath,
} from "@/lib/planTreeUtils";

type RightPanel = "gallery" | "detail" | "params";

function rightPanelHeading(
  panel: RightPanel,
  creatorForSelected: unknown,
  browsingCreator: unknown,
): string {
  if (panel === "params" && creatorForSelected) return "Parameters";
  if (panel === "detail" && browsingCreator) return "Creator Info";
  return "Creator Catalog";
}

export default function ConstructionPlansPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const { aeroplanes } = useAeroplanes();
  const { creators } = useCreators();

  const [viewMode, setViewMode] = useState<"templates" | "plans">("templates");
  const { plans: templates, mutate: mutateTemplates } = useConstructionPlans("template");
  const { plans: aeroplanePlans, mutate: mutateAeroplanePlans } = useAeroplanePlans(aeroplaneId);
  const activePlans = viewMode === "templates" ? templates : aeroplanePlans;
  const activeMutate = viewMode === "templates" ? mutateTemplates : mutateAeroplanePlans;

  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const { plan, mutate: mutatePlan } = useConstructionPlan(selectedPlanId);

  const [rightPanel, setRightPanel] = useState<RightPanel>("gallery");
  const [selectedStepPath, setSelectedStepPath] = useState<string | null>(null);
  const [selectedStepNode, setSelectedStepNode] = useState<PlanStepNode | null>(null);
  const [browsingCreator, setBrowsingCreator] = useState<CreatorInfo | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addingCreator, setAddingCreator] = useState<CreatorInfo | null>(null);
  const [addCreatorId, setAddCreatorId] = useState("");
  const [addCreatorIdManual, setAddCreatorIdManual] = useState(false);
  const [addStepParams, setAddStepParams] = useState<Record<string, unknown>>({});

  // Debounce timer for parameter saves
  const paramSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Execute state
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<ExecutionResult | null>(null);
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);
  const [executeAeroplaneId, setExecuteAeroplaneId] = useState<string>("");

  // New Plan dialog state
  const [newPlanDialogOpen, setNewPlanDialogOpen] = useState(false);
  const [newPlanName, setNewPlanName] = useState("");
  const [newPlanFromTemplate, setNewPlanFromTemplate] = useState(false);
  const [newPlanTemplateId, setNewPlanTemplateId] = useState<number | null>(null);

  // CadViewer modal state
  const [cadViewerOpen, setCadViewerOpen] = useState(false);
  const [cadViewerFullscreen, setCadViewerFullscreen] = useState(false);
  const [cadViewerData, setCadViewerData] = useState<Record<string, unknown> | null>(null);

  // ── Helpers ─────────────────────────────────────────────────────

  function findCreatorForStep(step: PlanStepNode): CreatorInfo | undefined {
    return creators.find((c) => c.class_name === step.creator_id || c.class_name === step.$TYPE);
  }

  // ── Plan CRUD ───────────────────────────────────────────────────

  function handleNewPlan() {
    if (viewMode === "plans") {
      // Open the new plan dialog with template selection
      setNewPlanName("");
      setNewPlanFromTemplate(false);
      setNewPlanTemplateId(null);
      setNewPlanDialogOpen(true);
    } else {
      // Templates mode: simple prompt (no template-from-template)
      const name = prompt("Template name:");
      if (!name?.trim()) return;
      createPlan({
        name: name.trim(),
        tree_json: { $TYPE: "ConstructionRootNode", creator_id: "root", successors: [] },
        plan_type: "template",
      })
        .then((created) => {
          activeMutate();
          setSelectedPlanId(created.id);
        })
        .catch((err) => alert(err instanceof Error ? err.message : "Failed to create template"));
    }
  }

  async function handleNewPlanSubmit() {
    const name = newPlanName.trim();
    if (!name) return;
    if (newPlanFromTemplate && newPlanTemplateId != null && !aeroplaneId) return;
    try {
      let created;
      if (newPlanFromTemplate && newPlanTemplateId != null && aeroplaneId) {
        created = await instantiateTemplate(aeroplaneId, newPlanTemplateId, name);
        mutateAeroplanePlans();
      } else {
        created = await createPlan({
          name,
          tree_json: { $TYPE: "ConstructionRootNode", creator_id: "root", successors: [] },
          plan_type: "plan",
          aeroplane_id: aeroplaneId ?? undefined,
        });
        activeMutate();
      }
      setSelectedPlanId(created.id);
      setNewPlanDialogOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create plan");
    }
  }

  async function handleDeletePlan() {
    if (!selectedPlanId || !plan) return;
    if (!confirm(`Delete plan "${plan.name}"?`)) return;
    try {
      await deletePlan(selectedPlanId);
      setSelectedPlanId(null);
      setSelectedStepPath(null);
      setSelectedStepNode(null);
      activeMutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete plan");
    }
  }

  // ── Step operations ─────────────────────────────────────────────

  const handleSelectStep = useCallback(
    (path: string, node: PlanStepNode) => {
      setSelectedStepPath(path);
      setSelectedStepNode(node);
      setRightPanel("params");
    },
    [],
  );

  async function handleDeleteStep(path: string) {
    if (!plan || !selectedPlanId) return;
    const treeJson = plan.tree_json as unknown as PlanStepNode;
    const updated = deleteStepAtPath(treeJson, path);
    try {
      await updatePlan(selectedPlanId, {
        name: plan.name,
        description: plan.description ?? undefined,
        tree_json: updated as unknown as Record<string, unknown>,
      });
      mutatePlan();
      activeMutate();
      if (selectedStepPath === path) {
        setSelectedStepPath(null);
        setSelectedStepNode(null);
        setRightPanel("gallery");
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete step");
    }
  }

  async function handleAddCreator(creator: CreatorInfo, creatorId?: string) {
    if (!plan || !selectedPlanId) return;
    const treeJson = plan.tree_json as unknown as PlanStepNode;
    const newStep: PlanStepNode = {
      $TYPE: creator.class_name,
      creator_id: creatorId || creator.suggested_id || creator.class_name,
      ...addStepParams,
      successors: [],
    };
    const updatedTree: PlanStepNode = {
      ...treeJson,
      successors: [...(treeJson.successors ?? []), newStep],
    };
    try {
      await updatePlan(selectedPlanId, {
        name: plan.name,
        description: plan.description ?? undefined,
        tree_json: updatedTree as unknown as Record<string, unknown>,
      });
      mutatePlan();
      activeMutate();
      setAddDialogOpen(false);
      setAddingCreator(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add step");
    }
  }

  function handleParamChange(key: string, value: unknown) {
    if (!plan || !selectedPlanId || !selectedStepPath || !selectedStepNode) return;
    const updatedNode = { ...selectedStepNode, [key]: value };
    setSelectedStepNode(updatedNode);

    // Debounce the API call to avoid flooding on every keystroke
    if (paramSaveTimer.current) clearTimeout(paramSaveTimer.current);
    paramSaveTimer.current = setTimeout(() => {
      const treeJson = plan.tree_json as unknown as PlanStepNode;
      const updated = updateNodeAtPath(treeJson, selectedStepPath, updatedNode);
      updatePlan(selectedPlanId, {
        name: plan.name,
        description: plan.description ?? undefined,
        tree_json: updated as unknown as Record<string, unknown>,
      })
        .then(() => mutatePlan())
        .catch((err) => alert(err instanceof Error ? err.message : "Failed to save parameter"));
    }, 400);
  }

  function handleReorder(fromPath: string, toPath: string) {
    if (!plan || !selectedPlanId) return;
    const treeJson = plan.tree_json as unknown as PlanStepNode;
    const fromNode = getStepAtPath(treeJson, fromPath);
    if (!fromNode) return;
    const withoutFrom = deleteStepAtPath(treeJson, fromPath);
    const adjustedToPath = computeReorderTargetPath(fromPath, toPath);
    const updated = insertStepAtPath(withoutFrom, adjustedToPath, fromNode);

    updatePlan(selectedPlanId, {
      name: plan.name,
      description: plan.description ?? undefined,
      tree_json: updated as unknown as Record<string, unknown>,
    })
      .then(() => {
        mutatePlan();
        activeMutate();
      })
      .catch((err) => alert(err instanceof Error ? err.message : "Failed to reorder"));
  }

  // ── Execute ─────────────────────────────────────────────────────

  async function handleExecute() {
    if (!selectedPlanId || !executeAeroplaneId) return;
    setExecuting(true);
    setExecuteResult(null);
    try {
      const result = await executePlan(executeAeroplaneId, selectedPlanId);
      setExecuteResult(result);
      // Open CadViewer modal if tessellation data is available
      if (result.status === "success" && result.tessellation) {
        setCadViewerData(result.tessellation);
        setCadViewerOpen(true);
      }
    } catch (err) {
      setExecuteResult({
        status: "error",
        shape_keys: [],
        export_paths: [],
        error: err instanceof Error ? err.message : "Execution failed",
        duration_ms: 0,
        tessellation: null,
      });
    } finally {
      setExecuting(false);
    }
  }

  // ── Template / Plan conversion ──────────────────────────────────

  async function handleInstantiateTemplate() {
    if (!selectedPlanId || !aeroplaneId) return;
    try {
      const created = await instantiateTemplate(aeroplaneId, selectedPlanId);
      mutateAeroplanePlans();
      setViewMode("plans");
      setSelectedPlanId(created.id);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create plan");
    }
  }

  async function handleSaveAsTemplate() {
    if (!selectedPlanId || !aeroplaneId) return;
    try {
      await toTemplate(aeroplaneId, selectedPlanId);
      mutateTemplates();
      alert("Template created successfully");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to save as template");
    }
  }

  // ── Render ──────────────────────────────────────────────────────

  const treeJson = plan?.tree_json as unknown as PlanStepNode | null;
  const stepCount = treeJson?.successors?.length ?? 0;
  const creatorForSelected = selectedStepNode
    ? findCreatorForStep(selectedStepNode)
    : null;

  return (
    <>
      <WorkbenchTwoPanel>
        {/* Left panel: toggle + plan selector + tree */}
        <div className="flex h-full flex-col gap-3 overflow-hidden">
          {/* Template / Plans toggle */}
          <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1 self-start">
            <button
              onClick={() => {
                setViewMode("templates");
                setSelectedPlanId(null);
                setSelectedStepPath(null);
                setSelectedStepNode(null);
                setRightPanel("gallery");
              }}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
                viewMode === "templates"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <BookTemplate size={12} />
              Templates
            </button>
            <button
              onClick={() => {
                setViewMode("plans");
                setSelectedPlanId(null);
                setSelectedStepPath(null);
                setSelectedStepNode(null);
                setRightPanel("gallery");
              }}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
                viewMode === "plans"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Hammer size={12} />
              Plans
            </button>
          </div>

          {/* Plan selector */}
          <div className="flex items-center gap-2">
            <select
              value={selectedPlanId ?? ""}
              onChange={(e) => {
                const id = e.target.value ? Number.parseInt(e.target.value, 10) : null;
                setSelectedPlanId(id);
                setSelectedStepPath(null);
                setSelectedStepNode(null);
                setRightPanel("gallery");
              }}
              className="flex-1 rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground"
            >
              <option value="">
                {viewMode === "templates" ? "Select a template..." : "Select a plan..."}
              </option>
              {activePlans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.step_count} steps)
                </option>
              ))}
            </select>
            <button
              onClick={handleNewPlan}
              title={viewMode === "templates" ? "New template" : "New plan"}
              className="flex size-8 items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90"
            >
              <Plus size={14} />
            </button>
          </div>

          {/* Action buttons */}
          {selectedPlanId && plan && (
            <div className="flex items-center gap-2">
              {viewMode === "plans" && (
                <button
                  onClick={() => {
                    setExecuteAeroplaneId(aeroplaneId ?? "");
                    setExecuteDialogOpen(true);
                    setExecuteResult(null);
                  }}
                  className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90"
                >
                  <Play size={12} />
                  Execute
                </button>
              )}
              {viewMode === "templates" && aeroplaneId && (
                <button
                  onClick={handleInstantiateTemplate}
                  className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90"
                >
                  <Copy size={12} />
                  Create Plan
                </button>
              )}
              {viewMode === "plans" && aeroplaneId && (
                <button
                  onClick={handleSaveAsTemplate}
                  className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
                >
                  <BookTemplate size={12} />
                  Save as Template
                </button>
              )}
              <span className="flex-1" />
              <button
                onClick={handleDeletePlan}
                className="flex size-7 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20"
                title={viewMode === "templates" ? "Delete template" : "Delete plan"}
              >
                <Trash2 size={12} />
              </button>
            </div>
          )}

          {/* Plan tree */}
          {selectedPlanId && plan ? (
            <PlanTree
              planName={plan.name}
              treeJson={treeJson}
              stepCount={stepCount}
              selectedStepPath={selectedStepPath}
              onSelectStep={handleSelectStep}
              onDeleteStep={handleDeleteStep}
              onAddStep={() => setAddDialogOpen(true)}
              onReorder={handleReorder}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-[13px] text-muted-foreground">
                {viewMode === "templates"
                  ? "Select or create a template"
                  : "Select or create a plan"}
              </p>
            </div>
          )}
        </div>

        {/* Right panel: gallery, detail view, or param editor */}
        <div className="flex min-h-0 w-full flex-1 flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2.5">
            <Hammer className="size-5 text-primary" />
            <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
              {rightPanelHeading(rightPanel, creatorForSelected, browsingCreator)}
            </h1>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              {rightPanel === "gallery" ? `${creators.length} creators` : ""}
            </span>
          </div>

          {rightPanel === "params" && selectedStepNode && creatorForSelected ? (
            <div className="flex flex-col gap-4">
              <button
                onClick={() => setRightPanel("gallery")}
                className="self-start text-[11px] text-primary hover:underline"
              >
                &larr; Back to catalog
              </button>
              <CreatorParameterForm
                creatorName={creatorForSelected.class_name}
                creatorDescription={creatorForSelected.description}
                params={creatorForSelected.parameters}
                values={selectedStepNode as unknown as Record<string, unknown>}
                onChange={handleParamChange}
                availableShapeKeys={collectAvailableShapeKeys(treeJson, creators, selectedStepPath)}
              />
              <label className="flex flex-col gap-1 mt-2">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                  Comment
                </span>
                <textarea
                  value={String(selectedStepNode?._comment ?? "")}
                  onChange={(e) => handleParamChange("_comment", e.target.value)}
                  placeholder="Notes about this step..."
                  rows={3}
                  className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none resize-none"
                />
              </label>
            </div>
          ) : rightPanel === "detail" && browsingCreator ? (
            <CreatorDetailView
              creator={browsingCreator}
              onBack={() => {
                setBrowsingCreator(null);
                setRightPanel("gallery");
              }}
            />
          ) : (
            <CreatorGallery
              creators={creators}
              onSelect={(creator) => {
                setBrowsingCreator(creator);
                setRightPanel("detail");
              }}
            />
          )}
        </div>
      </WorkbenchTwoPanel>

      <AddStepDialog
        open={addDialogOpen}
        addingCreator={addingCreator}
        addCreatorId={addCreatorId}
        addCreatorIdManual={addCreatorIdManual}
        addStepParams={addStepParams}
        treeJson={treeJson}
        creators={creators}
        onClose={() => { setAddDialogOpen(false); setAddingCreator(null); }}
        onSetAddingCreator={setAddingCreator}
        onSetAddCreatorId={setAddCreatorId}
        onSetAddCreatorIdManual={setAddCreatorIdManual}
        onSetAddStepParams={setAddStepParams}
        onAddCreator={handleAddCreator}
      />

      <NewPlanDialog
        open={newPlanDialogOpen}
        newPlanName={newPlanName}
        newPlanFromTemplate={newPlanFromTemplate}
        newPlanTemplateId={newPlanTemplateId}
        templates={templates}
        onClose={() => setNewPlanDialogOpen(false)}
        onSetNewPlanName={setNewPlanName}
        onSetNewPlanFromTemplate={setNewPlanFromTemplate}
        onSetNewPlanTemplateId={setNewPlanTemplateId}
        onSubmit={handleNewPlanSubmit}
      />

      <ExecuteDialog
        open={executeDialogOpen}
        executeAeroplaneId={executeAeroplaneId}
        executing={executing}
        executeResult={executeResult}
        aeroplanes={aeroplanes}
        onClose={() => setExecuteDialogOpen(false)}
        onSetExecuteAeroplaneId={setExecuteAeroplaneId}
        onExecute={handleExecute}
      />

      <CadViewerModal
        open={cadViewerOpen}
        fullscreen={cadViewerFullscreen}
        cadViewerData={cadViewerData}
        executeResult={executeResult}
        onClose={() => { setCadViewerOpen(false); setCadViewerFullscreen(false); }}
        onToggleFullscreen={() => setCadViewerFullscreen((v) => !v)}
      />
    </>
  );
}

// ── Extracted dialog components ──────────────────────────────────

interface AddStepDialogProps {
  open: boolean;
  addingCreator: CreatorInfo | null;
  addCreatorId: string;
  addCreatorIdManual: boolean;
  addStepParams: Record<string, unknown>;
  treeJson: PlanStepNode | null;
  creators: CreatorInfo[];
  onClose: () => void;
  onSetAddingCreator: (c: CreatorInfo | null) => void;
  onSetAddCreatorId: (id: string) => void;
  onSetAddCreatorIdManual: (v: boolean) => void;
  onSetAddStepParams: (p: Record<string, unknown>) => void;
  onAddCreator: (creator: CreatorInfo, creatorId?: string) => void;
}

function AddStepDialog({
  open,
  addingCreator,
  addCreatorId,
  addCreatorIdManual,
  addStepParams,
  treeJson,
  creators,
  onClose,
  onSetAddingCreator,
  onSetAddCreatorId,
  onSetAddCreatorIdManual,
  onSetAddStepParams,
  onAddCreator,
}: Readonly<AddStepDialogProps>) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label={addingCreator ? `Add ${addingCreator.class_name}` : "Add Step"}
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        className="flex max-h-[85vh] w-[600px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        {addingCreator ? (
          <>
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Add {addingCreator.class_name}
            </h2>
            <label className="flex flex-col gap-1">
              <span className="flex items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                Step ID (creator_id)
                {addCreatorIdManual && addingCreator.suggested_id && (
                  <button
                    onClick={() => {
                      onSetAddCreatorIdManual(false);
                      onSetAddCreatorId(resolveIdTemplate(addingCreator.suggested_id!, addStepParams));
                    }}
                    className="text-[9px] text-primary hover:underline"
                  >
                    Reset
                  </button>
                )}
              </span>
              <input
                type="text"
                value={addCreatorId}
                onChange={(e) => {
                  onSetAddCreatorId(e.target.value);
                  onSetAddCreatorIdManual(true);
                }}
                placeholder={addingCreator.suggested_id ?? addingCreator.class_name}
                className="rounded-lg border border-border bg-input px-3 py-2 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none"
              />
              <span className="text-[9px] text-subtle-foreground">
                This ID is used to reference this step&apos;s output shapes in subsequent steps.
              </span>
            </label>
            {addingCreator.parameters.length > 0 && (
              <CreatorParameterForm
                creatorName=""
                params={addingCreator.parameters}
                values={addStepParams}
                onChange={(key, value) => {
                  const next = { ...addStepParams, [key]: value };
                  onSetAddStepParams(next);
                  if (!addCreatorIdManual && addingCreator.suggested_id) {
                    onSetAddCreatorId(resolveIdTemplate(addingCreator.suggested_id, next));
                  }
                }}
                availableShapeKeys={collectAvailableShapeKeys(treeJson, creators)}
              />
            )}
            <details className="rounded-xl border border-border">
              <summary className="cursor-pointer px-3 py-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                Creator Info
              </summary>
              <div className="px-3 pb-3">
                <CreatorDetailView
                  creator={addingCreator}
                  onBack={() => onSetAddingCreator(null)}
                />
              </div>
            </details>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => onSetAddingCreator(null)}
                className="rounded-full border border-border px-4 py-2 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
              >
                Back
              </button>
              <button
                onClick={() => {
                  const id = addCreatorId.trim() || addingCreator.suggested_id || addingCreator.class_name;
                  onAddCreator({ ...addingCreator } as CreatorInfo, id);
                }}
                className="rounded-full bg-primary px-4 py-2 text-[12px] text-primary-foreground hover:opacity-90"
              >
                Add Step
              </button>
            </div>
          </>
        ) : (
          <>
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Add Step
            </h2>
            <CreatorGallery
              creators={creators}
              onSelect={(creator) => {
                const defaults: Record<string, unknown> = {};
                for (const p of creator.parameters) {
                  if (p.default != null) defaults[p.name] = p.default;
                }
                onSetAddStepParams(defaults);
                onSetAddingCreator(creator);
                onSetAddCreatorIdManual(false);
                onSetAddCreatorId(
                  creator.suggested_id
                    ? resolveIdTemplate(creator.suggested_id, defaults)
                    : creator.class_name,
                );
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}

interface NewPlanDialogProps {
  open: boolean;
  newPlanName: string;
  newPlanFromTemplate: boolean;
  newPlanTemplateId: number | null;
  templates: Array<{ id: number; name: string; step_count: number; description?: string | null }>;
  onClose: () => void;
  onSetNewPlanName: (v: string) => void;
  onSetNewPlanFromTemplate: (v: boolean) => void;
  onSetNewPlanTemplateId: (v: number | null) => void;
  onSubmit: () => void;
}

function NewPlanDialog({
  open,
  newPlanName,
  newPlanFromTemplate,
  newPlanTemplateId,
  templates,
  onClose,
  onSetNewPlanName,
  onSetNewPlanFromTemplate,
  onSetNewPlanTemplateId,
  onSubmit,
}: Readonly<NewPlanDialogProps>) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="New Plan"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        className="flex w-[480px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
          New Plan
        </h2>
        <label className="flex flex-col gap-1">
          <span className="text-[12px] text-muted-foreground">Plan name</span>
          <input
            type="text"
            value={newPlanName}
            onChange={(e) => onSetNewPlanName(e.target.value)}
            placeholder="Enter plan name..."
            autoFocus
            className="rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground outline-none"
          />
        </label>
        <fieldset className="flex flex-col gap-2">
          <span className="text-[12px] text-muted-foreground">Start from</span>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="newPlanSource"
              checked={!newPlanFromTemplate}
              onChange={() => {
                onSetNewPlanFromTemplate(false);
                onSetNewPlanTemplateId(null);
              }}
              className="accent-[#FF8400]"
            />
            <span className="text-[12px] text-foreground">Empty plan</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="newPlanSource"
              checked={newPlanFromTemplate}
              onChange={() => onSetNewPlanFromTemplate(true)}
              className="accent-[#FF8400]"
            />
            <span className="text-[12px] text-foreground">From template</span>
          </label>
        </fieldset>
        {newPlanFromTemplate && (
          <div className="flex flex-col gap-2">
            <select
              value={newPlanTemplateId ?? ""}
              onChange={(e) =>
                onSetNewPlanTemplateId(e.target.value ? Number.parseInt(e.target.value, 10) : null)
              }
              className="rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground"
            >
              <option value="">Select a template...</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.step_count} steps)
                </option>
              ))}
            </select>
            {newPlanTemplateId != null &&
              templates.find((t) => t.id === newPlanTemplateId)?.description && (
                <p className="text-[11px] text-muted-foreground">
                  {templates.find((t) => t.id === newPlanTemplateId)?.description}
                </p>
              )}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-full border border-border px-4 py-2 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={
              !newPlanName.trim() ||
              (newPlanFromTemplate && newPlanTemplateId == null)
            }
            className="rounded-full bg-primary px-4 py-2 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}

interface ExecuteDialogProps {
  open: boolean;
  executeAeroplaneId: string;
  executing: boolean;
  executeResult: ExecutionResult | null;
  aeroplanes: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSetExecuteAeroplaneId: (v: string) => void;
  onExecute: () => void;
}

function ExecuteDialog({
  open,
  executeAeroplaneId,
  executing,
  executeResult,
  aeroplanes,
  onClose,
  onSetExecuteAeroplaneId,
  onExecute,
}: Readonly<ExecuteDialogProps>) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label="Execute Plan"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        className="flex w-[480px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
          Execute Plan
        </h2>
        <label className="flex flex-col gap-1">
          <span className="text-[12px] text-muted-foreground">Aeroplane</span>
          <select
            value={executeAeroplaneId}
            onChange={(e) => onSetExecuteAeroplaneId(e.target.value)}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground"
          >
            <option value="">Select aeroplane...</option>
            {aeroplanes.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>

        {executeResult && (
          <div
            className={`rounded-xl border p-3 text-[12px] ${
              executeResult.status === "success"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-red-500/30 bg-red-500/10 text-red-400"
            }`}
          >
            <p className="font-semibold">
              {executeResult.status === "success" ? "Success" : "Error"}
            </p>
            {executeResult.error && <p>{executeResult.error}</p>}
            {executeResult.shape_keys.length > 0 && (
              <p>Shapes: {executeResult.shape_keys.join(", ")}</p>
            )}
            {executeResult.duration_ms > 0 && (
              <p>Duration: {executeResult.duration_ms}ms</p>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-full border border-border px-4 py-2 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Close
          </button>
          <button
            onClick={onExecute}
            disabled={!executeAeroplaneId || executing}
            className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {executing ? (
              <>
                <Loader2 size={12} className="animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play size={12} />
                Execute
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

interface CadViewerModalProps {
  open: boolean;
  fullscreen: boolean;
  cadViewerData: Record<string, unknown> | null;
  executeResult: ExecutionResult | null;
  onClose: () => void;
  onToggleFullscreen: () => void;
}

function CadViewerModal({
  open,
  fullscreen,
  cadViewerData,
  executeResult,
  onClose,
  onToggleFullscreen,
}: Readonly<CadViewerModalProps>) {
  if (!open || !cadViewerData) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center ${fullscreen ? "" : "bg-black/60"}`}
      role="dialog"
      aria-modal="true"
      aria-label="Execution Result"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        className={`flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl ${
          fullscreen ? "h-full w-full rounded-none border-0" : "h-[80vh] w-[80vw]"
        }`}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
            Execution Result
          </span>
          {executeResult && (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
              {executeResult.shape_keys.length} shapes · {executeResult.duration_ms}ms
            </span>
          )}
          <div className="flex-1" />
          <button
            onClick={onToggleFullscreen}
            className="flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-sidebar-accent"
            title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button
            onClick={onClose}
            className="flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-sidebar-accent"
          >
            <X size={14} />
          </button>
        </div>
        <div className="min-h-0 flex-1">
          <CadViewer parts={[cadViewerData]} />
        </div>
      </div>
    </div>
  );
}
