# Construction Plans Tab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Tab 5 "Construction Plans" to the workbench — a two-panel UI for creating, editing, and executing JSON-defined construction workflows against aeroplanes.

**Architecture:** Two-panel layout (WorkbenchTwoPanel) with a plan tree on the left (TreeCard + SimpleTreeRow + DnD reordering) and a creator gallery + parameter form on the right. Plans are fetched/mutated via SWR hooks calling the existing `/construction-plans` REST API. No cross-panel drag-and-drop — steps are added via a creator selection dialog.

**Tech Stack:** Next.js App Router, React 19, SWR, @dnd-kit/core, Tailwind CSS, Vitest + React Testing Library

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/hooks/useConstructionPlans.ts` | SWR hooks for plan list, single plan, CRUD mutations |
| Create | `frontend/hooks/useCreators.ts` | SWR hook for creator catalog |
| Create | `frontend/app/workbench/construction-plans/page.tsx` | Page component — orchestrates tree, gallery, dialogs |
| Create | `frontend/components/workbench/PlanTree.tsx` | Plan step tree with DnD reordering |
| Create | `frontend/components/workbench/CreatorGallery.tsx` | Creator catalog grid with search + category filter |
| Create | `frontend/components/workbench/CreatorParameterForm.tsx` | Dynamic parameter form for a selected step |
| Modify | `frontend/components/workbench/Header.tsx:15-19` | Add tab 5 to STEPS array |
| Create | `frontend/__tests__/ConstructionPlansPage.test.tsx` | Page-level tests |
| Create | `frontend/__tests__/CreatorGallery.test.tsx` | Gallery search + filter tests |

---

### Task 1: SWR Hooks — useConstructionPlans + useCreators

**Files:**
- Create: `frontend/hooks/useConstructionPlans.ts`
- Create: `frontend/hooks/useCreators.ts`

- [ ] **Step 1: Create useConstructionPlans hook**

```typescript
// frontend/hooks/useConstructionPlans.ts
"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface PlanSummary {
  id: number;
  name: string;
  description: string | null;
  step_count: number;
  created_at: string;
}

export interface PlanRead {
  id: number;
  name: string;
  description: string | null;
  tree_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ExecutionResult {
  status: "success" | "error";
  shape_keys: string[];
  export_paths: string[];
  error: string | null;
  duration_ms: number;
}

export function useConstructionPlans() {
  const { data, error, isLoading, mutate } = useSWR<PlanSummary[]>(
    "/construction-plans",
    fetcher,
  );

  return {
    plans: data ?? [],
    error,
    isLoading,
    mutate,
  };
}

export function useConstructionPlan(id: number | null) {
  const { data, error, isLoading, mutate } = useSWR<PlanRead>(
    id != null ? `/construction-plans/${id}` : null,
    fetcher,
  );

  return {
    plan: data ?? null,
    error,
    isLoading,
    mutate,
  };
}

export async function createPlan(
  body: { name: string; description?: string; tree_json: Record<string, unknown> },
): Promise<PlanRead> {
  const res = await fetch(`${API_BASE}/construction-plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Create plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function updatePlan(
  id: number,
  body: { name: string; description?: string; tree_json: Record<string, unknown> },
): Promise<PlanRead> {
  const res = await fetch(`${API_BASE}/construction-plans/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Update plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function deletePlan(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/construction-plans/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Delete plan failed: ${res.status} ${detail}`);
  }
}

export async function executePlan(
  id: number,
  aeroplaneId: string,
): Promise<ExecutionResult> {
  const res = await fetch(`${API_BASE}/construction-plans/${id}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aeroplane_id: aeroplaneId }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Execute plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}
```

- [ ] **Step 2: Create useCreators hook**

```typescript
// frontend/hooks/useCreators.ts
"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export interface CreatorParam {
  name: string;
  type: string;
  default: unknown;
  required: boolean;
}

export interface CreatorInfo {
  class_name: string;
  category: string;
  description: string | null;
  parameters: CreatorParam[];
}

export const CREATOR_CATEGORIES = [
  "wing",
  "fuselage",
  "cad_operations",
  "export_import",
  "components",
] as const;

export type CreatorCategory = (typeof CREATOR_CATEGORIES)[number];

export function useCreators() {
  const { data, error, isLoading } = useSWR<CreatorInfo[]>(
    "/construction-plans/creators",
    fetcher,
  );

  return {
    creators: data ?? [],
    error,
    isLoading,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/hooks/useConstructionPlans.ts frontend/hooks/useCreators.ts
git commit -m "feat(gh#113): SWR hooks for construction plans + creators"
```

---

### Task 2: Header — Add Tab 5

**Files:**
- Modify: `frontend/components/workbench/Header.tsx:15-20`

- [ ] **Step 1: Add "Plans" tab to STEPS array**

In `frontend/components/workbench/Header.tsx`, change the STEPS array from:

```typescript
const STEPS = [
  { num: 1, label: "Mission", href: "/workbench/mission" },
  { num: 2, label: "Construction", href: "/workbench" },
  { num: 3, label: "Analysis", href: "/workbench/analysis" },
  { num: 4, label: "Components", href: "/workbench/components" },
] as const;
```

to:

```typescript
const STEPS = [
  { num: 1, label: "Mission", href: "/workbench/mission" },
  { num: 2, label: "Construction", href: "/workbench" },
  { num: 3, label: "Analysis", href: "/workbench/analysis" },
  { num: 4, label: "Components", href: "/workbench/components" },
  { num: 5, label: "Plans", href: "/workbench/construction-plans" },
] as const;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/workbench/Header.tsx
git commit -m "feat(gh#113): add Plans tab to workbench header"
```

---

### Task 3: CreatorGallery Component

**Files:**
- Create: `frontend/components/workbench/CreatorGallery.tsx`
- Create: `frontend/__tests__/CreatorGallery.test.tsx`

- [ ] **Step 1: Write failing test for CreatorGallery**

```typescript
// frontend/__tests__/CreatorGallery.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Search: icon, Plus: icon, ChevronDown: icon, ChevronRight: icon,
  };
});

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import type { CreatorInfo } from "@/hooks/useCreators";

const MOCK_CREATORS: CreatorInfo[] = [
  {
    class_name: "VaseModeWingCreator",
    category: "wing",
    description: "Vase-mode wing with ribs, spars, TEDs",
    parameters: [
      { name: "wing_index", type: "str", default: null, required: true },
    ],
  },
  {
    class_name: "ExportToStepCreator",
    category: "export_import",
    description: "Export shape to STEP file",
    parameters: [
      { name: "file_path", type: "str", default: null, required: true },
      { name: "shape_key", type: "str", default: null, required: true },
    ],
  },
  {
    class_name: "Fuse2ShapesCreator",
    category: "cad_operations",
    description: "Boolean union of two shapes",
    parameters: [
      { name: "shape_key_a", type: "str", default: null, required: true },
      { name: "shape_key_b", type: "str", default: null, required: true },
    ],
  },
];

describe("CreatorGallery", () => {
  it("renders all creators when no filter is active", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
    expect(screen.getByText("ExportToStepCreator")).toBeDefined();
    expect(screen.getByText("Fuse2ShapesCreator")).toBeDefined();
  });

  it("filters creators by search text", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search creators...");
    fireEvent.change(input, { target: { value: "vase" } });
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
    expect(screen.queryByText("ExportToStepCreator")).toBeNull();
  });

  it("filters creators by category tab", () => {
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={vi.fn()} />);
    fireEvent.click(screen.getByText("Export"));
    expect(screen.getByText("ExportToStepCreator")).toBeDefined();
    expect(screen.queryByText("VaseModeWingCreator")).toBeNull();
  });

  it("calls onSelect when a creator card is clicked", () => {
    const onSelect = vi.fn();
    render(<CreatorGallery creators={MOCK_CREATORS} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("VaseModeWingCreator"));
    expect(onSelect).toHaveBeenCalledWith(MOCK_CREATORS[0]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/CreatorGallery.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement CreatorGallery**

```typescript
// frontend/components/workbench/CreatorGallery.tsx
"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import type { CreatorInfo, CreatorCategory } from "@/hooks/useCreators";
import { CREATOR_CATEGORIES } from "@/hooks/useCreators";

const CATEGORY_LABELS: Record<CreatorCategory, string> = {
  wing: "Wing",
  fuselage: "Fuselage",
  cad_operations: "CAD Ops",
  export_import: "Export",
  components: "Components",
};

interface CreatorGalleryProps {
  creators: CreatorInfo[];
  onSelect: (creator: CreatorInfo) => void;
}

export function CreatorGallery({ creators, onSelect }: CreatorGalleryProps) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<CreatorCategory | null>(null);

  const filtered = creators.filter((c) => {
    if (category && c.category !== category) return false;
    if (search && !c.class_name.toLowerCase().includes(search.toLowerCase()))
      return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-3">
      {/* Search */}
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        <Search className="size-3.5 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search creators..."
          className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
        />
      </div>

      {/* Category tabs */}
      <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1 self-start flex-wrap">
        <button
          onClick={() => setCategory(null)}
          className={`rounded-full px-3 py-1 text-[11px] ${
            category === null
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          All
        </button>
        {CREATOR_CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`rounded-full px-3 py-1 text-[11px] ${
              category === cat
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <p className="py-8 text-center text-[13px] text-muted-foreground">
          No creators match your filter
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {filtered.map((creator) => (
            <button
              key={creator.class_name}
              onClick={() => onSelect(creator)}
              className="flex flex-col gap-1 rounded-xl border border-border bg-card p-3 text-left hover:border-primary/50 hover:bg-sidebar-accent"
            >
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                {creator.class_name}
              </span>
              <span className="rounded-full bg-card-muted px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground self-start">
                {CATEGORY_LABELS[creator.category as CreatorCategory] ?? creator.category}
              </span>
              {creator.description && (
                <span className="text-[10px] text-subtle-foreground line-clamp-2">
                  {creator.description}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/CreatorGallery.test.tsx`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/CreatorGallery.tsx frontend/__tests__/CreatorGallery.test.tsx
git commit -m "feat(gh#113): CreatorGallery component with search + category filter"
```

---

### Task 4: CreatorParameterForm Component

**Files:**
- Create: `frontend/components/workbench/CreatorParameterForm.tsx`

- [ ] **Step 1: Implement CreatorParameterForm**

This component renders a dynamic form for a plan step's parameters, based on the creator's parameter definitions.

```typescript
// frontend/components/workbench/CreatorParameterForm.tsx
"use client";

import type { CreatorParam } from "@/hooks/useCreators";

interface CreatorParameterFormProps {
  creatorName: string;
  params: CreatorParam[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}

export function CreatorParameterForm({
  creatorName,
  params,
  values,
  onChange,
}: CreatorParameterFormProps) {
  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
        {creatorName}
      </h3>
      {params.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">No parameters</p>
      ) : (
        params.map((param) => (
          <label key={param.name} className="flex flex-col gap-1">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
              {param.name}
              {param.required && <span className="text-primary"> *</span>}
              <span className="ml-1 text-[9px] text-subtle-foreground">
                ({param.type})
              </span>
            </span>
            {param.type === "bool" ? (
              <input
                type="checkbox"
                checked={Boolean(values[param.name] ?? param.default ?? false)}
                onChange={(e) => onChange(param.name, e.target.checked)}
                className="size-4"
              />
            ) : param.type === "int" || param.type === "float" ? (
              <input
                type="number"
                value={String(values[param.name] ?? param.default ?? "")}
                onChange={(e) => {
                  const v = param.type === "int"
                    ? parseInt(e.target.value, 10)
                    : parseFloat(e.target.value);
                  onChange(param.name, isNaN(v) ? null : v);
                }}
                step={param.type === "float" ? "any" : "1"}
                className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
              />
            ) : (
              <input
                type="text"
                value={String(values[param.name] ?? param.default ?? "")}
                onChange={(e) => onChange(param.name, e.target.value)}
                className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
              />
            )}
          </label>
        ))
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/workbench/CreatorParameterForm.tsx
git commit -m "feat(gh#113): CreatorParameterForm — dynamic param editing"
```

---

### Task 5: PlanTree Component

**Files:**
- Create: `frontend/components/workbench/PlanTree.tsx`

- [ ] **Step 1: Implement PlanTree**

The plan tree renders the `tree_json` as a flat list of SimpleTreeRow nodes with DnD reordering. `tree_json` uses `$TYPE` + `successors` for nesting.

```typescript
// frontend/components/workbench/PlanTree.tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/workbench/PlanTree.tsx
git commit -m "feat(gh#113): PlanTree component with DnD reordering"
```

---

### Task 6: Construction Plans Page

**Files:**
- Create: `frontend/app/workbench/construction-plans/page.tsx`

- [ ] **Step 1: Implement the page**

```typescript
// frontend/app/workbench/construction-plans/page.tsx
"use client";

import { useState, useCallback } from "react";
import { Hammer, Plus, Trash2, Play, Loader2 } from "lucide-react";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { PlanTree, type PlanStepNode } from "@/components/workbench/PlanTree";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import { CreatorParameterForm } from "@/components/workbench/CreatorParameterForm";
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

type RightPanel = "gallery" | "params";

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
  const [addDialogOpen, setAddDialogOpen] = useState(false);

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
    // Debounced save — update immediately in state, PUT on blur or next action
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
    }).then(() => {
      mutatePlan();
    });
  }

  function handleReorder(fromPath: string, toPath: string) {
    // Simple swap for MVP: move the step from fromPath to after toPath
    if (!plan || !selectedPlanId) return;
    const treeJson = plan.tree_json as unknown as PlanStepNode;
    const fromNode = getStepAtPath(treeJson, fromPath);
    if (!fromNode) return;
    const withoutFrom = deleteStepAtPath(treeJson, fromPath);
    // Insert after toPath at the same level (root successors for now)
    const toIdx = parseInt(toPath.replace("root.", ""), 10);
    const newSuccessors = [...(withoutFrom.successors ?? [])];
    newSuccessors.splice(isNaN(toIdx) ? newSuccessors.length : toIdx + 1, 0, fromNode);
    const updated = { ...withoutFrom, successors: newSuccessors };

    updatePlan(selectedPlanId, {
      name: plan.name,
      description: plan.description ?? undefined,
      tree_json: updated as unknown as Record<string, unknown>,
    }).then(() => {
      mutatePlan();
      mutatePlans();
    });
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

        {/* Right panel: gallery or params */}
        <div className="flex w-full flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2.5">
            <Hammer className="size-5 text-primary" />
            <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
              {rightPanel === "params" && creatorForSelected
                ? "Parameters"
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
                params={creatorForSelected.parameters}
                values={selectedStepNode as unknown as Record<string, unknown>}
                onChange={handleParamChange}
              />
            </div>
          ) : (
            <CreatorGallery
              creators={creators}
              onSelect={(creator) => {
                if (selectedPlanId && plan) {
                  handleAddCreator(creator);
                }
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/workbench/construction-plans/page.tsx
git commit -m "feat(gh#113): Construction Plans page — two-panel with CRUD + execute"
```

---

### Task 7: Page-Level Tests

**Files:**
- Create: `frontend/__tests__/ConstructionPlansPage.test.tsx`

- [ ] **Step 1: Write page tests**

```typescript
// frontend/__tests__/ConstructionPlansPage.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Hammer: icon, Plus: icon, Trash2: icon, Play: icon, Loader2: icon,
    Search: icon, ChevronDown: icon, ChevronRight: icon, Pencil: icon,
    Scale: icon,
  };
});

const mockMutatePlans = vi.fn();
const mockMutatePlan = vi.fn();
const mockCreatePlan = vi.fn().mockResolvedValue({ id: 99, name: "Test Plan" });
const mockDeletePlan = vi.fn().mockResolvedValue(undefined);
const mockExecutePlan = vi.fn().mockResolvedValue({
  status: "success",
  shape_keys: ["wing_left"],
  export_paths: [],
  error: null,
  duration_ms: 1234,
});

vi.mock("@/hooks/useConstructionPlans", () => ({
  useConstructionPlans: () => ({
    plans: [
      { id: 1, name: "eHawk Wing", description: null, step_count: 3, created_at: "2026-01-01" },
    ],
    error: null,
    isLoading: false,
    mutate: mockMutatePlans,
  }),
  useConstructionPlan: (id: number | null) => ({
    plan: id === 1
      ? {
          id: 1,
          name: "eHawk Wing",
          description: null,
          tree_json: {
            $TYPE: "ConstructionRootNode",
            creator_id: "root",
            successors: [
              { $TYPE: "VaseModeWingCreator", creator_id: "VaseModeWingCreator", wing_index: "main_wing", successors: [] },
            ],
          },
          created_at: "2026-01-01",
          updated_at: "2026-01-01",
        }
      : null,
    error: null,
    isLoading: false,
    mutate: mockMutatePlan,
  }),
  createPlan: (...args: unknown[]) => mockCreatePlan(...args),
  updatePlan: vi.fn().mockResolvedValue({}),
  deletePlan: (...args: unknown[]) => mockDeletePlan(...args),
  executePlan: (...args: unknown[]) => mockExecutePlan(...args),
}));

vi.mock("@/hooks/useCreators", () => ({
  useCreators: () => ({
    creators: [
      {
        class_name: "VaseModeWingCreator",
        category: "wing",
        description: "Vase-mode wing",
        parameters: [{ name: "wing_index", type: "str", default: null, required: true }],
      },
    ],
    error: null,
    isLoading: false,
  }),
  CREATOR_CATEGORIES: ["wing", "fuselage", "cad_operations", "export_import", "components"],
}));

vi.mock("@/hooks/useAeroplanes", () => ({
  useAeroplanes: () => ({
    aeroplanes: [
      { id: "aero-1", name: "eHawk", total_mass_kg: null, created_at: "", updated_at: "" },
    ],
    error: null,
    isLoading: false,
    mutate: vi.fn(),
    createAeroplane: vi.fn(),
    deleteAeroplane: vi.fn(),
  }),
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: null,
    selectedXsecIndex: null,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: vi.fn(),
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

import ConstructionPlansPage from "@/app/workbench/construction-plans/page";

beforeEach(() => {
  vi.clearAllMocks();
  // Reset window.prompt and window.confirm
  vi.spyOn(window, "prompt").mockReturnValue("Test Plan");
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("ConstructionPlansPage", () => {
  it("renders the plan selector with existing plans", () => {
    render(<ConstructionPlansPage />);
    expect(screen.getByText("eHawk Wing (3 steps)")).toBeDefined();
  });

  it("shows plan tree when a plan is selected", () => {
    render(<ConstructionPlansPage />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "1" } });
    expect(screen.getByText("VaseModeWingCreator")).toBeDefined();
  });

  it("shows Execute and Delete buttons when a plan is selected", () => {
    render(<ConstructionPlansPage />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
    expect(screen.getByText("Execute")).toBeDefined();
  });

  it("creates a new plan via prompt", async () => {
    render(<ConstructionPlansPage />);
    // Click the + button (the primary-colored one next to the selector)
    const buttons = screen.getAllByTitle("New plan");
    fireEvent.click(buttons[0]);
    await waitFor(() => {
      expect(mockCreatePlan).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Test Plan" }),
      );
    });
  });

  it("opens execute dialog and shows aeroplane selector", () => {
    render(<ConstructionPlansPage />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
    fireEvent.click(screen.getByText("Execute"));
    expect(screen.getByText("Execute Plan")).toBeDefined();
    expect(screen.getByText("eHawk")).toBeDefined();
  });

  it("shows creator catalog on the right panel", () => {
    render(<ConstructionPlansPage />);
    expect(screen.getByText("Creator Catalog")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run tests**

Run: `cd frontend && npx vitest run __tests__/ConstructionPlansPage.test.tsx __tests__/CreatorGallery.test.tsx`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/ConstructionPlansPage.test.tsx
git commit -m "test(gh#113): page-level + gallery tests for Construction Plans tab"
```

---

### Task 8: Verify + Final Commit

- [ ] **Step 1: Run all frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: All existing tests still pass + 10 new tests pass

- [ ] **Step 2: Run linter**

```bash
cd frontend && npx next lint
```

- [ ] **Step 3: Verify the page renders (manual check)**

Start the dev server and navigate to `/workbench/construction-plans`. Verify:
- Tab 5 "Plans" appears in header
- Plan selector shows
- Creator catalog renders on the right
- Creating a new plan works (requires backend running)

- [ ] **Step 4: Final commit if any lint fixes needed**

```bash
git add -A
git commit -m "chore(gh#113): lint fixes"
```
