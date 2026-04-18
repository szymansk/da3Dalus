"use client";

import { useState, useCallback, useRef } from "react";
import { Hammer, Plus, Trash2, Play, Loader2 } from "lucide-react";
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
  createPlan,
  updatePlan,
  deletePlan,
  executePlan,
  type ExecutionResult,
} from "@/hooks/useConstructionPlans";
import { useCreators, type CreatorInfo } from "@/hooks/useCreators";

type RightPanel = "gallery" | "detail" | "params";

export default function ConstructionPlansPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const { aeroplanes } = useAeroplanes();
  const { plans, mutate: mutatePlans } = useConstructionPlans();
  const { creators } = useCreators();

  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const { plan, mutate: mutatePlan } = useConstructionPlan(selectedPlanId);

  const [rightPanel, setRightPanel] = useState<RightPanel>("gallery");
  const [selectedStepPath, setSelectedStepPath] = useState<string | null>(null);
  const [selectedStepNode, setSelectedStepNode] = useState<PlanStepNode | null>(null);
  const [browsingCreator, setBrowsingCreator] = useState<CreatorInfo | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  // Debounce timer for parameter saves
  const paramSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Execute state
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<ExecutionResult | null>(null);
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);
  const [executeAeroplaneId, setExecuteAeroplaneId] = useState<string>("");

  // ── Helpers ─────────────────────────────────────────────────────

  function getStepAtPath(tree: PlanStepNode, path: string): PlanStepNode | null {
    if (path === "root") return tree;
    const parts = path.replace("root.", "").split(".");
    let current: PlanStepNode = tree;
    for (const part of parts) {
      const idx = parseInt(part, 10);
      if (!current.successors || !current.successors[idx]) return null;
      current = current.successors[idx];
    }
    return current;
  }

  function findCreatorForStep(step: PlanStepNode): CreatorInfo | undefined {
    return creators.find((c) => c.class_name === step.creator_id || c.class_name === step.$TYPE);
  }

  // ── Plan CRUD ───────────────────────────────────────────────────

  async function handleNewPlan() {
    const name = prompt("Plan name:");
    if (!name?.trim()) return;
    try {
      const created = await createPlan({
        name: name.trim(),
        tree_json: { $TYPE: "ConstructionRootNode", creator_id: "root", successors: [] },
      });
      mutatePlans();
      setSelectedPlanId(created.id);
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
      mutatePlans();
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

  function deleteStepAtPath(tree: PlanStepNode, path: string): PlanStepNode {
    if (path === "root") return { ...tree, successors: [] };
    const parts = path.replace("root.", "").split(".");
    const lastIdx = parseInt(parts[parts.length - 1], 10);
    const parentPath = parts.slice(0, -1);

    function navigate(node: PlanStepNode, remaining: string[]): PlanStepNode {
      if (remaining.length === 0) {
        const newSuccessors = [...(node.successors ?? [])];
        newSuccessors.splice(lastIdx, 1);
        return { ...node, successors: newSuccessors };
      }
      const idx = parseInt(remaining[0], 10);
      const newSuccessors = [...(node.successors ?? [])];
      newSuccessors[idx] = navigate(newSuccessors[idx], remaining.slice(1));
      return { ...node, successors: newSuccessors };
    }

    return navigate(tree, parentPath);
  }

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
      mutatePlans();
      if (selectedStepPath === path) {
        setSelectedStepPath(null);
        setSelectedStepNode(null);
        setRightPanel("gallery");
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete step");
    }
  }

  async function handleAddCreator(creator: CreatorInfo) {
    if (!plan || !selectedPlanId) return;
    const treeJson = plan.tree_json as unknown as PlanStepNode;
    const newStep: PlanStepNode = {
      $TYPE: creator.class_name,
      creator_id: creator.class_name,
      successors: [],
    };
    // Add default values for required params
    for (const param of creator.parameters) {
      if (param.default != null) {
        newStep[param.name] = param.default;
      }
    }
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
      mutatePlans();
      setAddDialogOpen(false);
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

      function updateNodeAtPath(node: PlanStepNode, path: string): PlanStepNode {
        if (path === "root") return updatedNode;
        const parts = path.replace("root.", "").split(".");
        const idx = parseInt(parts[0], 10);
        const rest = parts.slice(1).join(".");
        const newSuccessors = [...(node.successors ?? [])];
        newSuccessors[idx] = rest
          ? updateNodeAtPath(newSuccessors[idx], rest)
          : updatedNode;
        return { ...node, successors: newSuccessors };
      }

      const updated = updateNodeAtPath(treeJson, selectedStepPath);
      updatePlan(selectedPlanId, {
        name: plan.name,
        description: plan.description ?? undefined,
        tree_json: updated as unknown as Record<string, unknown>,
      })
        .then(() => mutatePlan())
        .catch((err) => alert(err instanceof Error ? err.message : "Failed to save parameter"));
    }, 400);
  }

  function insertStepAtPath(
    tree: PlanStepNode,
    path: string,
    step: PlanStepNode,
  ): PlanStepNode {
    // Insert step after the node at `path` within the same parent
    if (path === "root") {
      return { ...tree, successors: [...(tree.successors ?? []), step] };
    }
    const parts = path.replace("root.", "").split(".");
    const insertIdx = parseInt(parts[parts.length - 1], 10) + 1;
    const parentParts = parts.slice(0, -1);

    function navigate(node: PlanStepNode, remaining: string[]): PlanStepNode {
      if (remaining.length === 0) {
        const newSuccessors = [...(node.successors ?? [])];
        newSuccessors.splice(insertIdx, 0, step);
        return { ...node, successors: newSuccessors };
      }
      const idx = parseInt(remaining[0], 10);
      const newSuccessors = [...(node.successors ?? [])];
      newSuccessors[idx] = navigate(newSuccessors[idx], remaining.slice(1));
      return { ...node, successors: newSuccessors };
    }

    return navigate(tree, parentParts);
  }

  function handleReorder(fromPath: string, toPath: string) {
    if (!plan || !selectedPlanId) return;
    const treeJson = plan.tree_json as unknown as PlanStepNode;
    const fromNode = getStepAtPath(treeJson, fromPath);
    if (!fromNode) return;
    const withoutFrom = deleteStepAtPath(treeJson, fromPath);
    const updated = insertStepAtPath(withoutFrom, toPath, fromNode);

    updatePlan(selectedPlanId, {
      name: plan.name,
      description: plan.description ?? undefined,
      tree_json: updated as unknown as Record<string, unknown>,
    })
      .then(() => {
        mutatePlan();
        mutatePlans();
      })
      .catch((err) => alert(err instanceof Error ? err.message : "Failed to reorder"));
  }

  // ── Execute ─────────────────────────────────────────────────────

  async function handleExecute() {
    if (!selectedPlanId || !executeAeroplaneId) return;
    setExecuting(true);
    setExecuteResult(null);
    try {
      const result = await executePlan(selectedPlanId, executeAeroplaneId);
      setExecuteResult(result);
    } catch (err) {
      setExecuteResult({
        status: "error",
        shape_keys: [],
        export_paths: [],
        error: err instanceof Error ? err.message : "Execution failed",
        duration_ms: 0,
      });
    } finally {
      setExecuting(false);
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
        {/* Left panel: plan selector + tree */}
        <div className="flex h-full flex-col gap-3 overflow-hidden">
          {/* Plan selector */}
          <div className="flex items-center gap-2">
            <select
              value={selectedPlanId ?? ""}
              onChange={(e) => {
                const id = e.target.value ? parseInt(e.target.value, 10) : null;
                setSelectedPlanId(id);
                setSelectedStepPath(null);
                setSelectedStepNode(null);
                setRightPanel("gallery");
              }}
              className="flex-1 rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground"
            >
              <option value="">Select a plan...</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.step_count} steps)
                </option>
              ))}
            </select>
            <button
              onClick={handleNewPlan}
              title="New plan"
              className="flex size-8 items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90"
            >
              <Plus size={14} />
            </button>
          </div>

          {/* Action buttons */}
          {selectedPlanId && plan && (
            <div className="flex items-center gap-2">
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
              <span className="flex-1" />
              <button
                onClick={handleDeletePlan}
                className="flex size-7 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20"
                title="Delete plan"
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
                Select or create a plan
              </p>
            </div>
          )}
        </div>

        {/* Right panel: gallery, detail view, or param editor */}
        <div className="flex w-full flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2.5">
            <Hammer className="size-5 text-primary" />
            <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
              {rightPanel === "params" && creatorForSelected
                ? "Parameters"
                : rightPanel === "detail" && browsingCreator
                ? "Creator Info"
                : "Creator Catalog"}
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
              />
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

      {/* Add Step Dialog */}
      {addDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setAddDialogOpen(false)}
        >
          <div
            className="flex max-h-[85vh] w-[600px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Add Step
            </h2>
            <CreatorGallery
              creators={creators}
              onSelect={handleAddCreator}
            />
          </div>
        </div>
      )}

      {/* Execute Dialog */}
      {executeDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setExecuteDialogOpen(false)}
        >
          <div
            className="flex w-[480px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Execute Plan
            </h2>
            <label className="flex flex-col gap-1">
              <span className="text-[12px] text-muted-foreground">Aeroplane</span>
              <select
                value={executeAeroplaneId}
                onChange={(e) => setExecuteAeroplaneId(e.target.value)}
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
                onClick={() => setExecuteDialogOpen(false)}
                className="rounded-full border border-border px-4 py-2 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
              >
                Close
              </button>
              <button
                onClick={handleExecute}
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
      )}
    </>
  );
}
