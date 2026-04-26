# Construction Plans: Component Split (#324) & Modal Alignment (#329)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 1065-line `page.tsx` click-dummy into focused components, then align the parameter edit modal to the project's standard dialog pattern.

**Architecture:** Extract five components from `page.tsx` into `frontend/components/workbench/construction-plans/`. The page becomes a thin coordinator (~150 lines). The EditParamsModal gets restructured to match the header/body/footer pattern used by `ComponentEditDialog` and other dialogs.

**Tech Stack:** React 19, Next.js 16 App Router, TypeScript, Tailwind CSS, lucide-react icons, `useDialog` hook.

**Branch:** `refactor/gh-324-split-construction-plans` (off `feat/gh-323-click-dummy-construction-plans`)

**Important context:**
- This is a **click-dummy** with mock data — no backend calls, no real API integration yet.
- The branch base is the click-dummy branch, NOT main. Main doesn't have these frontend changes.
- All components use the project's dark theme (orange accent `#FF8400`, JetBrains Mono + Geist fonts).
- Existing patterns to follow: `TreeCard`, `SimpleTreeRow`, `useDialog`, `ComponentEditDialog`.
- `frontend/AGENTS.md` warns that Next.js APIs may differ from training data — check `node_modules/next/dist/docs/` before writing any code.

---

## File Structure

After this plan, the construction-plans area will look like:

```
frontend/
├── app/workbench/construction-plans/
│   └── page.tsx                          # MODIFY — slim coordinator (~150 lines)
└── components/workbench/construction-plans/
    ├── types.ts                          # CREATE — mock types + data
    ├── PlanTreeSection.tsx               # CREATE — single plan tree with recursive creator rendering
    ├── TemplateSelector.tsx              # CREATE — searchable dropdown for template selection
    ├── TemplateModePanel.tsx             # CREATE — template mode left panel
    └── EditParamsModal.tsx               # CREATE — parameter editing modal (aligned to standard pattern)
```

No test files — this is a click-dummy with mock data. Tests will be added when real API integration happens.

---

## Task 1: Create types.ts — Extract mock types and data

**Files:**
- Create: `frontend/components/workbench/construction-plans/types.ts`

This file holds all the mock interfaces and hardcoded data. It will be replaced with real API types later.

- [ ] **Step 1: Create the directory**

```bash
mkdir -p frontend/components/workbench/construction-plans
```

- [ ] **Step 2: Create `types.ts`**

Create `frontend/components/workbench/construction-plans/types.ts` with the following content. Copy lines 28–404 from `page.tsx` — the mock interfaces and constants:

```typescript
// Mock types for click-dummy — will be replaced with real API types

export interface MockShape {
  name: string;
  direction: "input" | "output";
}

export interface MockCreatorNode {
  creatorClassName: string;
  creatorId: string;
  shapes: MockShape[];
  mockParams: Record<string, unknown>;
  successors?: MockCreatorNode[];
}

export interface MockPlan {
  id: number;
  name: string;
  creators: MockCreatorNode[];
}

export interface MockTemplate {
  id: number;
  name: string;
  creators: MockCreatorNode[];
}

export const MOCK_PLANS: MockPlan[] = [
  {
    id: 1,
    name: "Wing Construction",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "vase_wing",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "vase_wing", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
      {
        creatorClassName: "ScaleRotateTranslateCreator",
        creatorId: "mirror_wing",
        shapes: [
          { name: "vase_wing", direction: "input" },
          { name: "mirrored_wing", direction: "output" },
        ],
        mockParams: { loglevel: 50, source_shape: "vase_wing" },
      },
    ],
  },
  {
    id: 2,
    name: "Fuselage Build",
    creators: [
      {
        creatorClassName: "FuselageShellShapeCreator",
        creatorId: "main_fuselage",
        shapes: [
          { name: "fuselage_config", direction: "input" },
          { name: "fuselage_shell", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
    ],
  },
  {
    id: 3,
    name: "Motor Mount",
    creators: [
      {
        creatorClassName: "EngineMountShapeCreator",
        creatorId: "mount_base",
        shapes: [{ name: "mount_base", direction: "output" }],
        mockParams: { loglevel: 50 },
      },
      {
        creatorClassName: "Cut2ShapesCreator",
        creatorId: "motor_cutout",
        shapes: [
          { name: "mount_base", direction: "input" },
          { name: "motor_cutout", direction: "output" },
        ],
        mockParams: { loglevel: 50, minuend: "mount_base" },
      },
    ],
  },
  {
    id: 4,
    name: "Wing Assembly Pipeline",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "raw_wing",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "raw_wing", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
        successors: [
          {
            creatorClassName: "ScaleRotateTranslateCreator",
            creatorId: "positioned_wing",
            shapes: [
              { name: "raw_wing", direction: "input" },
              { name: "positioned_wing", direction: "output" },
            ],
            mockParams: { loglevel: 50, source_shape: "raw_wing" },
            successors: [
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "servo_cutout_left",
                shapes: [
                  { name: "positioned_wing", direction: "input" },
                  { name: "servo_cutout_left", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
              },
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "servo_cutout_right",
                shapes: [
                  { name: "positioned_wing", direction: "input" },
                  { name: "servo_cutout_right", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
              },
              {
                creatorClassName: "SimpleOffsetShapeCreator",
                creatorId: "wing_shell",
                shapes: [
                  { name: "positioned_wing", direction: "input" },
                  { name: "wing_shell", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
                successors: [
                  {
                    creatorClassName: "FuseMultipleShapesCreator",
                    creatorId: "wing_with_servos",
                    shapes: [
                      { name: "wing_shell", direction: "input" },
                      { name: "servo_cutout_left", direction: "input" },
                      { name: "servo_cutout_right", direction: "input" },
                      { name: "wing_with_servos", direction: "output" },
                    ],
                    mockParams: { loglevel: 50 },
                    successors: [
                      {
                        creatorClassName: "RepairFacesShapeCreator",
                        creatorId: "wing_repaired",
                        shapes: [
                          { name: "wing_with_servos", direction: "input" },
                          { name: "wing_repaired", direction: "output" },
                        ],
                        mockParams: { loglevel: 50 },
                        successors: [
                          {
                            creatorClassName: "ExportToStepCreator",
                            creatorId: "wing_step_export",
                            shapes: [{ name: "wing_repaired", direction: "input" }],
                            mockParams: { loglevel: 50, output_dir: "./step" },
                          },
                          {
                            creatorClassName: "ExportToStlCreator",
                            creatorId: "wing_stl_export",
                            shapes: [{ name: "wing_repaired", direction: "input" }],
                            mockParams: { loglevel: 50, output_dir: "./stl" },
                          },
                          {
                            creatorClassName: "ExportTo3mfCreator",
                            creatorId: "wing_3mf_export",
                            shapes: [{ name: "wing_repaired", direction: "input" }],
                            mockParams: { loglevel: 50, output_dir: "./3mf" },
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
          {
            creatorClassName: "StandWingSegmentOnPrinterCreator",
            creatorId: "print_orientation",
            shapes: [
              { name: "raw_wing", direction: "input" },
              { name: "print_ready_wing", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
            successors: [
              {
                creatorClassName: "ExportToStlCreator",
                creatorId: "print_stl_export",
                shapes: [{ name: "print_ready_wing", direction: "input" }],
                mockParams: { loglevel: 50, output_dir: "./print" },
              },
            ],
          },
        ],
      },
      {
        creatorClassName: "WingLoftCreator",
        creatorId: "wing_loft",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "wing_loft_solid", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
        successors: [
          {
            creatorClassName: "ServoImporterCreator",
            creatorId: "servo_left",
            shapes: [
              { name: "wing_loft_solid", direction: "input" },
              { name: "servo_left_shape", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
          },
          {
            creatorClassName: "ServoImporterCreator",
            creatorId: "servo_right",
            shapes: [
              { name: "wing_loft_solid", direction: "input" },
              { name: "servo_right_shape", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
          },
          {
            creatorClassName: "ComponentImporterCreator",
            creatorId: "spar_carbon_tube",
            shapes: [
              { name: "wing_loft_solid", direction: "input" },
              { name: "spar_shape", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
          },
        ],
      },
    ],
  },
  {
    id: 5,
    name: "Deep Nesting Stress Test",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "depth_01_wing",
        shapes: [{ name: "depth_01", direction: "output" }],
        mockParams: { loglevel: 50 },
        successors: [
          {
            creatorClassName: "ScaleRotateTranslateCreator",
            creatorId: "depth_02_transform",
            shapes: [
              { name: "depth_01", direction: "input" },
              { name: "depth_02", direction: "output" },
            ],
            mockParams: { loglevel: 50 },
            successors: [
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "depth_03_cut",
                shapes: [
                  { name: "depth_02", direction: "input" },
                  { name: "depth_03", direction: "output" },
                ],
                mockParams: { loglevel: 50 },
                successors: [
                  {
                    creatorClassName: "SimpleOffsetShapeCreator",
                    creatorId: "depth_04_offset",
                    shapes: [
                      { name: "depth_03", direction: "input" },
                      { name: "depth_04", direction: "output" },
                    ],
                    mockParams: { loglevel: 50 },
                    successors: [
                      {
                        creatorClassName: "FuseMultipleShapesCreator",
                        creatorId: "depth_05_fuse",
                        shapes: [
                          { name: "depth_04", direction: "input" },
                          { name: "depth_05", direction: "output" },
                        ],
                        mockParams: { loglevel: 50 },
                        successors: [
                          {
                            creatorClassName: "RepairFacesShapeCreator",
                            creatorId: "depth_06_repair",
                            shapes: [
                              { name: "depth_05", direction: "input" },
                              { name: "depth_06", direction: "output" },
                            ],
                            mockParams: { loglevel: 50 },
                            successors: [
                              {
                                creatorClassName: "ScaleRotateTranslateCreator",
                                creatorId: "depth_07_reposition",
                                shapes: [
                                  { name: "depth_06", direction: "input" },
                                  { name: "depth_07", direction: "output" },
                                ],
                                mockParams: { loglevel: 50 },
                                successors: [
                                  {
                                    creatorClassName: "Intersect2ShapesCreator",
                                    creatorId: "depth_08_intersect",
                                    shapes: [
                                      { name: "depth_07", direction: "input" },
                                      { name: "depth_08", direction: "output" },
                                    ],
                                    mockParams: { loglevel: 50 },
                                    successors: [
                                      {
                                        creatorClassName: "AddMultipleShapesCreator",
                                        creatorId: "depth_09_compound",
                                        shapes: [
                                          { name: "depth_08", direction: "input" },
                                          { name: "depth_09", direction: "output" },
                                        ],
                                        mockParams: { loglevel: 50 },
                                        successors: [
                                          {
                                            creatorClassName: "ExportToStepCreator",
                                            creatorId: "depth_10_export",
                                            shapes: [{ name: "depth_09", direction: "input" }],
                                            mockParams: { loglevel: 50, output_dir: "./deep" },
                                          },
                                        ],
                                      },
                                    ],
                                  },
                                ],
                              },
                            ],
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
];

export const MOCK_TEMPLATES: MockTemplate[] = [
  {
    id: 101,
    name: "Standard Wing Template",
    creators: [
      {
        creatorClassName: "VaseModeWingCreator",
        creatorId: "vase_wing",
        shapes: [
          { name: "wing_config", direction: "input" },
          { name: "vase_wing", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
      {
        creatorClassName: "ScaleRotateTranslateCreator",
        creatorId: "mirror_wing",
        shapes: [
          { name: "vase_wing", direction: "input" },
          { name: "mirrored_wing", direction: "output" },
        ],
        mockParams: { loglevel: 50, source_shape: "vase_wing" },
      },
    ],
  },
  {
    id: 102,
    name: "Fuselage Pod Template",
    creators: [
      {
        creatorClassName: "FuselageShellShapeCreator",
        creatorId: "pod_body",
        shapes: [
          { name: "fuselage_config", direction: "input" },
          { name: "pod_body", direction: "output" },
        ],
        mockParams: { loglevel: 20 },
      },
    ],
  },
];

/** Count all creators recursively (including successors). */
export function countCreators(creators: MockCreatorNode[]): number {
  return creators.reduce(
    (sum, c) => sum + 1 + countCreators(c.successors ?? []),
    0,
  );
}
```

- [ ] **Step 3: Verify the file compiles**

```bash
cd frontend && npx tsc --noEmit components/workbench/construction-plans/types.ts 2>&1 | head -20
```

Expected: no errors (pure types + data, no React imports needed).

- [ ] **Step 4: Commit**

```bash
git add frontend/components/workbench/construction-plans/types.ts
git commit -m "refactor(gh-324): extract mock types and data to types.ts"
```

---

## Task 2: Create PlanTreeSection.tsx — Recursive creator tree rendering

**Files:**
- Create: `frontend/components/workbench/construction-plans/PlanTreeSection.tsx`

This component renders a single plan as a collapsible tree — the plan header row with action buttons, plus recursive creator node rendering with shapes. It corresponds to lines 776–948 of the original `page.tsx`.

- [ ] **Step 1: Create PlanTreeSection.tsx**

Create `frontend/components/workbench/construction-plans/PlanTreeSection.tsx`:

```tsx
"use client";

import { useCallback } from "react";
import {
  Play,
  Plus,
  BookTemplate,
  Pencil,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { SimpleTreeRow } from "@/components/workbench/SimpleTreeRow";
import type { MockCreatorNode, MockPlan, MockTemplate } from "./types";

interface PlanTreeSectionProps {
  plan: MockPlan | MockTemplate;
  expanded: boolean;
  onToggle: () => void;
  expandedCreators: Set<string>;
  onToggleCreator: (key: string) => void;
  onEditCreator: (planId: number, creator: MockCreatorNode) => void;
  /** Hide plan-level action buttons (used in template mode where actions are in the TreeCard header). */
  hidePlanActions?: boolean;
}

function renderCreatorTree(
  creator: MockCreatorNode,
  planId: number,
  level: number,
  expandedSet: Set<string>,
  toggleFn: (key: string) => void,
  onEdit: (planId: number, creator: MockCreatorNode) => void,
): React.ReactNode {
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

export function PlanTreeSection({
  plan,
  expanded,
  onToggle,
  expandedCreators,
  onToggleCreator,
  onEditCreator,
  hidePlanActions = false,
}: Readonly<PlanTreeSectionProps>) {
  const handleEdit = useCallback(
    (creator: MockCreatorNode) => onEditCreator(plan.id, creator),
    [onEditCreator, plan.id],
  );

  return (
    <div className="flex flex-col">
      {/* Plan header row */}
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

      {/* Creator tree (when plan is expanded) */}
      {expanded &&
        plan.creators.map((creator) =>
          renderCreatorTree(
            creator,
            plan.id,
            1,
            expandedCreators,
            onToggleCreator,
            (_, c) => handleEdit(c),
          ),
        )}

      {/* Separator between plans */}
      {!hidePlanActions && <div className="mx-2 my-1 border-b border-border/50" />}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workbench/construction-plans/PlanTreeSection.tsx
git commit -m "refactor(gh-324): extract PlanTreeSection component"
```

---

## Task 3: Create TemplateSelector.tsx — Searchable template dropdown

**Files:**
- Create: `frontend/components/workbench/construction-plans/TemplateSelector.tsx`

Extracted from lines 616–686 of `page.tsx`. No changes to behavior.

- [ ] **Step 1: Create TemplateSelector.tsx**

Create `frontend/components/workbench/construction-plans/TemplateSelector.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Search, ChevronDown } from "lucide-react";
import type { MockTemplate } from "./types";

interface TemplateSelectorProps {
  templates: MockTemplate[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function TemplateSelector({
  templates,
  selectedId,
  onSelect,
}: Readonly<TemplateSelectorProps>) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = templates.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()),
  );
  const selected = templates.find((t) => t.id === selectedId);

  return (
    <div className="relative">
      <div
        className="flex cursor-pointer items-center gap-2 rounded-xl border border-border bg-input px-3 py-2"
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => {
          if (e.key === "Enter") setOpen(!open);
        }}
        role="combobox"
        aria-expanded={open}
        tabIndex={0}
      >
        <Search className="size-3.5 text-muted-foreground" />
        <input
          type="text"
          value={open ? search : selected?.name ?? ""}
          onChange={(e) => {
            setSearch(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Select template..."
          className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
        />
        <ChevronDown size={12} className="text-muted-foreground" />
      </div>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-[200px] w-full overflow-y-auto rounded-xl border border-border bg-card shadow-lg">
          {filtered.length === 0 ? (
            <p className="px-3 py-2 text-[12px] text-muted-foreground">
              No templates found
            </p>
          ) : (
            filtered.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  onSelect(t.id);
                  setSearch("");
                  setOpen(false);
                }}
                className={`block w-full px-3 py-2 text-left text-[12px] hover:bg-sidebar-accent ${
                  t.id === selectedId
                    ? "bg-sidebar-accent text-primary"
                    : "text-foreground"
                }`}
              >
                <span className="font-[family-name:var(--font-jetbrains-mono)]">
                  {t.name}
                </span>
                <span className="ml-2 text-[10px] text-muted-foreground">
                  {t.creators.length} steps
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/workbench/construction-plans/TemplateSelector.tsx
git commit -m "refactor(gh-324): extract TemplateSelector component"
```

---

## Task 4: Create TemplateModePanel.tsx — Template mode left panel

**Files:**
- Create: `frontend/components/workbench/construction-plans/TemplateModePanel.tsx`

Extracted from lines 954–1029 of `page.tsx`. Composes `TemplateSelector`, `TreeCard`, and `PlanTreeSection`.

- [ ] **Step 1: Create TemplateModePanel.tsx**

Create `frontend/components/workbench/construction-plans/TemplateModePanel.tsx`:

```tsx
"use client";

import { Play, Pencil, Plus, PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { TreeCard } from "@/components/workbench/TreeCard";
import { TemplateSelector } from "./TemplateSelector";
import { PlanTreeSection } from "./PlanTreeSection";
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
  const selectedTemplate =
    templates.find((t) => t.id === selectedTemplateId) ?? null;

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
                onClick={() =>
                  alert("Play Template: would open aeroplane selector")
                }
                title="Execute template against an aeroplane"
                className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70"
              >
                <Play size={14} />
              </button>
              <button
                onClick={onToggleWide}
                title={
                  treeWide ? "Collapse tree panel" : "Expand tree panel"
                }
                className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent"
              >
                {treeWide ? (
                  <PanelLeftClose size={12} />
                ) : (
                  <PanelLeftOpen size={12} />
                )}
              </button>
            </>
          }
        >
          {/* Template root node */}
          <div className="group flex items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent">
            <span className="w-3 shrink-0" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[13px] font-medium text-foreground">
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
              onClick={() =>
                alert(`Add step to "${selectedTemplate.name}"`)
              }
              title={`Add step to ${selectedTemplate.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Plus size={10} />
            </button>
          </div>

          {/* Reuse PlanTreeSection for creator rendering, but skip the plan header */}
          {selectedTemplate.creators.map((creator) => {
            const creatorKey = `plan-${selectedTemplate.id}-${creator.creatorId}`;
            const hasChildren =
              creator.shapes.length > 0 ||
              (creator.successors ?? []).length > 0;

            return (
              <PlanTreeSection
                key={creatorKey}
                plan={selectedTemplate}
                expanded={true}
                onToggle={() => {}}
                expandedCreators={expandedCreators}
                onToggleCreator={onToggleCreator}
                onEditCreator={onEditCreator}
                hidePlanActions
              />
            );
          })}
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
```

**Wait — there's a problem.** The `TemplateModePanel` currently renders the template's creator nodes differently from plan mode: it has a separate root node row, then renders each creator directly (not via `PlanTreeSection` plan header). Let me fix this. The template panel should render creators directly using `renderCreatorTree` from `PlanTreeSection`, not wrap each creator in a full `PlanTreeSection` (which would show a plan header for each).

The cleanest approach: `PlanTreeSection` already handles the plan header + creator rendering. In template mode, the original code renders creators directly without the `PlanTreeSection` wrapper. So `TemplateModePanel` should import the `renderCreatorTree` function.

**Revised approach:** Export `renderCreatorTree` from `PlanTreeSection.tsx` and use it directly in `TemplateModePanel`.

Update the file to:

```tsx
"use client";

import { Play, Pencil, Plus, PanelLeftOpen, PanelLeftClose } from "lucide-react";
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
  const selectedTemplate =
    templates.find((t) => t.id === selectedTemplateId) ?? null;

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
                onClick={() =>
                  alert("Play Template: would open aeroplane selector")
                }
                title="Execute template against an aeroplane"
                className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70"
              >
                <Play size={14} />
              </button>
              <button
                onClick={onToggleWide}
                title={
                  treeWide ? "Collapse tree panel" : "Expand tree panel"
                }
                className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent"
              >
                {treeWide ? (
                  <PanelLeftClose size={12} />
                ) : (
                  <PanelLeftOpen size={12} />
                )}
              </button>
            </>
          }
        >
          {/* Template root node */}
          <div className="group flex items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent">
            <span className="w-3 shrink-0" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[13px] font-medium text-foreground">
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
              onClick={() =>
                alert(`Add step to "${selectedTemplate.name}"`)
              }
              title={`Add step to ${selectedTemplate.name}`}
              className="hidden size-5 items-center justify-center rounded-full text-muted-foreground hover:text-primary group-hover:flex"
            >
              <Plus size={10} />
            </button>
          </div>

          {/* Creator nodes */}
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
```

This means `renderCreatorTree` in `PlanTreeSection.tsx` must be exported. Update the function declaration in Task 2's code from:

```typescript
function renderCreatorTree(
```

to:

```typescript
export function renderCreatorTree(
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/workbench/construction-plans/TemplateModePanel.tsx
git commit -m "refactor(gh-324): extract TemplateModePanel component"
```

---

## Task 5: Create EditParamsModal.tsx — Aligned to standard dialog pattern (#329)

**Files:**
- Create: `frontend/components/workbench/construction-plans/EditParamsModal.tsx`

This extracts the EditParamsModal from `page.tsx` (lines 515–614) AND aligns it to the standard dialog pattern from `ComponentEditDialog.tsx`. The key structural changes:

1. **Header:** Add `border-b border-border px-6 py-4` section with title + close button
2. **Body:** Wrap content in `flex-1 flex flex-col overflow-hidden px-6 py-5`
3. **Footer:** Add `border-t border-border px-6 py-4` section with Cancel/Save buttons
4. **Close button:** Match standard `size-8 rounded-full` (not `size-7`)

- [ ] **Step 1: Create EditParamsModal.tsx**

Create `frontend/components/workbench/construction-plans/EditParamsModal.tsx`:

```tsx
"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CreatorParameterForm } from "@/components/workbench/CreatorParameterForm";
import type { CreatorInfo } from "@/hooks/useCreators";
import type { MockCreatorNode } from "./types";

interface EditParamsModalProps {
  open: boolean;
  creator: MockCreatorNode | null;
  creatorInfo: CreatorInfo | null;
  onClose: () => void;
}

export function EditParamsModal({
  open,
  creator,
  creatorInfo,
  onClose,
}: Readonly<EditParamsModalProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [values, setValues] = useState<Record<string, unknown>>({});

  // Reset values when creator changes
  const currentCreatorId = creator?.creatorId;
  const [lastCreatorId, setLastCreatorId] = useState<string | null>(null);
  if (currentCreatorId && currentCreatorId !== lastCreatorId) {
    setLastCreatorId(currentCreatorId);
    setValues(creator?.mockParams ?? {});
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={creator ? `Edit ${creator.creatorId}` : "Edit Parameters"}
    >
      {open && creator && (
        <div className="flex max-h-[85vh] w-[520px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Edit {creator.creatorId}
            </span>
            <span className="flex-1" />
            <button
              onClick={onClose}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
            {creator.shapes.length > 0 && (
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card-muted/30 p-3">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                  Shapes
                </span>
                {creator.shapes.map((s) => (
                  <div
                    key={`${s.direction}-${s.name}`}
                    className="flex items-center gap-2 text-[12px] text-muted-foreground"
                  >
                    {s.direction === "input" ? (
                      <ArrowDown size={10} className="text-blue-400" />
                    ) : (
                      <ArrowUp size={10} className="text-emerald-400" />
                    )}
                    <span className="font-[family-name:var(--font-jetbrains-mono)]">
                      {s.name}
                    </span>
                    <span className="text-[10px] text-subtle-foreground">
                      ({s.direction})
                    </span>
                  </div>
                ))}
              </div>
            )}

            {creatorInfo ? (
              <CreatorParameterForm
                creatorName={creatorInfo.class_name}
                creatorDescription={creatorInfo.description}
                params={creatorInfo.parameters}
                values={values}
                onChange={(key, value) =>
                  setValues((prev) => ({ ...prev, [key]: value }))
                }
                availableShapeKeys={creator.shapes
                  .filter((s) => s.direction === "output")
                  .map((s) => s.name)}
              />
            ) : (
              <p className="text-[12px] text-muted-foreground">
                Creator &quot;{creator.creatorClassName}&quot; not found in
                catalog.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
            <button
              onClick={onClose}
              className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
```

Key changes from the click-dummy version:
- Header section with `border-b border-border px-6 py-4` (was: no border, `p-6` on whole card)
- Body section with `px-6 py-5` and `overflow-y-auto` (was: mixed in with header/footer)
- Footer section with `border-t border-border px-6 py-4` (was: inline at bottom)
- Close button `size-8` (was: `size-7` — now matches `ComponentEditDialog`)
- Button text `text-[13px]` (was: `text-[12px]` — now matches `ComponentEditDialog`)

- [ ] **Step 2: Commit**

```bash
git add frontend/components/workbench/construction-plans/EditParamsModal.tsx
git commit -m "feat(gh-329): extract EditParamsModal with standard dialog layout"
```

---

## Task 6: Rewrite page.tsx — Slim coordinator

**Files:**
- Modify: `frontend/app/workbench/construction-plans/page.tsx` (full rewrite)

Replace the entire 1065-line file with a slim coordinator that imports and composes the extracted components. Target: ~150 lines.

- [ ] **Step 1: Rewrite page.tsx**

Replace the entire content of `frontend/app/workbench/construction-plans/page.tsx` with:

```tsx
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

export default function ConstructionPlansPage() {
  const { creators } = useCreators();

  // View mode toggle
  const [viewMode, setViewMode] = useState<"plans" | "templates">("plans");

  // Tree panel width: normal (360px) or wide (2/3 of screen)
  const [treeWide, setTreeWide] = useState(false);

  // Plan mode state
  const [expandedPlans, setExpandedPlans] = useState<Set<number>>(
    new Set([1, 4, 5]),
  );
  const [expandedCreators, setExpandedCreators] = useState<Set<string>>(
    new Set([
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
    ]),
  );

  // Template mode state
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(
    null,
  );
  const [templateExpandedCreators, setTemplateExpandedCreators] = useState<
    Set<string>
  >(new Set());

  // Edit modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingCreator, setEditingCreator] = useState<MockCreatorNode | null>(
    null,
  );

  const togglePlan = useCallback((planId: number) => {
    setExpandedPlans((prev) => {
      const next = new Set(prev);
      if (next.has(planId)) next.delete(planId);
      else next.add(planId);
      return next;
    });
  }, []);

  const toggleCreator = useCallback((creatorKey: string) => {
    setExpandedCreators((prev) => {
      const next = new Set(prev);
      if (next.has(creatorKey)) next.delete(creatorKey);
      else next.add(creatorKey);
      return next;
    });
  }, []);

  const toggleTemplateCreator = useCallback((creatorKey: string) => {
    setTemplateExpandedCreators((prev) => {
      const next = new Set(prev);
      if (next.has(creatorKey)) next.delete(creatorKey);
      else next.add(creatorKey);
      return next;
    });
  }, []);

  const handleEditCreator = useCallback(
    (_planId: number, creator: MockCreatorNode) => {
      setEditingCreator(creator);
      setEditModalOpen(true);
    },
    [],
  );

  const handleSelectTemplate = useCallback((id: number) => {
    setSelectedTemplateId(id);
    const template = MOCK_TEMPLATES.find((t) => t.id === id);
    if (template) {
      setTemplateExpandedCreators(
        new Set(template.creators.map((c) => `plan-${id}-${c.creatorId}`)),
      );
    }
  }, []);

  const editingCreatorInfo = editingCreator
    ? creators.find((c) => c.class_name === editingCreator.creatorClassName) ??
      null
    : null;

  const totalSteps = MOCK_PLANS.reduce(
    (sum, p) => sum + countCreators(p.creators),
    0,
  );

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
        {/* Left panel: plan/template trees */}
        <div
          className="flex min-h-0 shrink-0 flex-col overflow-hidden transition-all duration-300"
          style={{
            width: treeWide ? "66%" : 360,
            minWidth: treeWide ? "66%" : 360,
          }}
        >
          <div className="flex h-full flex-col gap-3 overflow-hidden">
            {/* Mode toggle */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-full border border-border bg-card p-1">
                <button
                  onClick={() => setViewMode("plans")}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
                    viewMode === "plans"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Hammer size={12} />
                  Plans
                </button>
                <button
                  onClick={() => setViewMode("templates")}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] ${
                    viewMode === "templates"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <BookTemplate size={12} />
                  Templates
                </button>
              </div>
            </div>

            {/* Plan mode */}
            {viewMode === "plans" && (
              <TreeCard
                title="Construction Plans"
                badge={`${totalSteps} steps`}
                actions={
                  <>
                    <button
                      onClick={() =>
                        alert("Execute All: would execute all plans")
                      }
                      title="Execute all plans"
                      className="flex size-6 items-center justify-center rounded-lg text-primary hover:text-primary/70"
                    >
                      <Play size={14} />
                    </button>
                    <button
                      onClick={() => setTreeWide((w) => !w)}
                      title={
                        treeWide
                          ? "Collapse tree panel"
                          : "Expand tree panel"
                      }
                      className="flex size-6 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-sidebar-accent"
                    >
                      {treeWide ? (
                        <PanelLeftClose size={12} />
                      ) : (
                        <PanelLeftOpen size={12} />
                      )}
                    </button>
                  </>
                }
              >
                {MOCK_PLANS.map((plan) => (
                  <PlanTreeSection
                    key={plan.id}
                    plan={plan}
                    expanded={expandedPlans.has(plan.id)}
                    onToggle={() => togglePlan(plan.id)}
                    expandedCreators={expandedCreators}
                    onToggleCreator={toggleCreator}
                    onEditCreator={handleEditCreator}
                  />
                ))}
              </TreeCard>
            )}

            {/* Template mode */}
            {viewMode === "templates" && (
              <TemplateModePanel
                templates={MOCK_TEMPLATES}
                selectedTemplateId={selectedTemplateId}
                onSelectTemplate={handleSelectTemplate}
                expandedCreators={templateExpandedCreators}
                onToggleCreator={toggleTemplateCreator}
                onEditCreator={handleEditCreator}
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
              alert(
                `Would add "${creator.class_name}" to plan via drag-and-drop`,
              )
            }
          />
        </div>
      </div>

      {/* Parameter edit modal */}
      <EditParamsModal
        open={editModalOpen}
        creator={editingCreator}
        creatorInfo={editingCreatorInfo}
        onClose={() => {
          setEditModalOpen(false);
          setEditingCreator(null);
        }}
      />
    </>
  );
}
```

- [ ] **Step 2: Verify the full app compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no type errors.

- [ ] **Step 3: Start dev server and verify in browser**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000/workbench/construction-plans` in a browser and verify:
- Plan mode shows all 5 plans, expanding/collapsing works
- Creator nodes show shapes, edit button opens modal
- Template mode shows dropdown selector, selecting a template renders its tree
- Panel expand/collapse toggle works
- Creator Gallery on the right still shows all creators
- Edit modal opens with correct parameters when clicking pencil icon
- Modal has header with border, scrollable body, footer with border

- [ ] **Step 4: Verify line count**

```bash
wc -l frontend/app/workbench/construction-plans/page.tsx
```

Expected: ~190 lines (under 200 target).

- [ ] **Step 5: Commit**

```bash
git add frontend/app/workbench/construction-plans/page.tsx
git commit -m "refactor(gh-324): slim page.tsx to coordinator importing extracted components

Closes #324
Closes #329"
```

---

## Self-Review Checklist

### Spec coverage

| #324 Acceptance Criteria | Task |
|--------------------------|------|
| page.tsx reduced to <200 lines | Task 6 (~190 lines) |
| Each extracted component has clear props interface | Tasks 2–5 (all have typed interfaces) |
| No functional regression | Task 6 step 3 (browser verification) |
| All existing tests still pass | No tests exist for click-dummy; type-check verification in Task 6 |

| #329 Acceptance Criteria | Task |
|--------------------------|------|
| Edit button on each Creator node opens modal dialog | Task 2 (`onEdit` prop on SimpleTreeRow) |
| Modal contains parameter form with current values | Task 5 (`CreatorParameterForm` with `values`) |
| Save updates the plan, Cancel discards | Task 5 (both call `onClose` — mock behavior preserved) |
| Consistent with AddStep dialog pattern (project standard) | Task 5 (header/body/footer with borders) |
| Inline parameter editing removed from tree view | Already not in click-dummy (edit is modal-only) |

### Placeholder scan

No TBDs, TODOs, or "implement later" found.

### Type consistency

- `MockCreatorNode`, `MockPlan`, `MockTemplate` — defined in `types.ts`, imported consistently across all files
- `renderCreatorTree` — defined and exported in `PlanTreeSection.tsx`, imported in `TemplateModePanel.tsx`
- `EditParamsModalProps` — uses `MockCreatorNode` and `CreatorInfo` consistently
- `countCreators` — defined in `types.ts`, imported in `page.tsx`
