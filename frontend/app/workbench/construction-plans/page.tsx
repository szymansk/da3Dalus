"use client";

import { useState, useCallback, useMemo } from "react";
import {
  Hammer,
  Play,
  Plus,
  BookTemplate,
  Pencil,
  ChevronDown,
  ChevronRight,
  ArrowDown,
  ArrowUp,
  Search,
  X,
  PanelLeftOpen,
  PanelLeftClose,
} from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import { CreatorParameterForm } from "@/components/workbench/CreatorParameterForm";
import { useCreators, type CreatorInfo } from "@/hooks/useCreators";
import { SimpleTreeRow, type SimpleTreeNode } from "@/components/workbench/SimpleTreeRow";
import { TreeCard } from "@/components/workbench/TreeCard";

// ── Mock data ──────────────────────────────────────────────────────

interface MockShape {
  name: string;
  direction: "input" | "output";
}

interface MockCreatorNode {
  creatorClassName: string;
  creatorId: string;
  shapes: MockShape[];
  mockParams: Record<string, unknown>;
  successors?: MockCreatorNode[];
}

interface MockPlan {
  id: number;
  name: string;
  creators: MockCreatorNode[];
}

interface MockTemplate {
  id: number;
  name: string;
  creators: MockCreatorNode[];
}

const MOCK_PLANS: MockPlan[] = [
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
        shapes: [
          { name: "mount_base", direction: "output" },
        ],
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
                            shapes: [
                              { name: "wing_repaired", direction: "input" },
                            ],
                            mockParams: { loglevel: 50, output_dir: "./step" },
                          },
                          {
                            creatorClassName: "ExportToStlCreator",
                            creatorId: "wing_stl_export",
                            shapes: [
                              { name: "wing_repaired", direction: "input" },
                            ],
                            mockParams: { loglevel: 50, output_dir: "./stl" },
                          },
                          {
                            creatorClassName: "ExportTo3mfCreator",
                            creatorId: "wing_3mf_export",
                            shapes: [
                              { name: "wing_repaired", direction: "input" },
                            ],
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
                shapes: [
                  { name: "print_ready_wing", direction: "input" },
                ],
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
            shapes: [{ name: "depth_01", direction: "input" }, { name: "depth_02", direction: "output" }],
            mockParams: { loglevel: 50 },
            successors: [
              {
                creatorClassName: "Cut2ShapesCreator",
                creatorId: "depth_03_cut",
                shapes: [{ name: "depth_02", direction: "input" }, { name: "depth_03", direction: "output" }],
                mockParams: { loglevel: 50 },
                successors: [
                  {
                    creatorClassName: "SimpleOffsetShapeCreator",
                    creatorId: "depth_04_offset",
                    shapes: [{ name: "depth_03", direction: "input" }, { name: "depth_04", direction: "output" }],
                    mockParams: { loglevel: 50 },
                    successors: [
                      {
                        creatorClassName: "FuseMultipleShapesCreator",
                        creatorId: "depth_05_fuse",
                        shapes: [{ name: "depth_04", direction: "input" }, { name: "depth_05", direction: "output" }],
                        mockParams: { loglevel: 50 },
                        successors: [
                          {
                            creatorClassName: "RepairFacesShapeCreator",
                            creatorId: "depth_06_repair",
                            shapes: [{ name: "depth_05", direction: "input" }, { name: "depth_06", direction: "output" }],
                            mockParams: { loglevel: 50 },
                            successors: [
                              {
                                creatorClassName: "ScaleRotateTranslateCreator",
                                creatorId: "depth_07_reposition",
                                shapes: [{ name: "depth_06", direction: "input" }, { name: "depth_07", direction: "output" }],
                                mockParams: { loglevel: 50 },
                                successors: [
                                  {
                                    creatorClassName: "Intersect2ShapesCreator",
                                    creatorId: "depth_08_intersect",
                                    shapes: [{ name: "depth_07", direction: "input" }, { name: "depth_08", direction: "output" }],
                                    mockParams: { loglevel: 50 },
                                    successors: [
                                      {
                                        creatorClassName: "AddMultipleShapesCreator",
                                        creatorId: "depth_09_compound",
                                        shapes: [{ name: "depth_08", direction: "input" }, { name: "depth_09", direction: "output" }],
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

const MOCK_TEMPLATES: MockTemplate[] = [
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

// ── Plan tree section ──────────────────────────────────────────────

interface PlanTreeSectionProps {
  plan: MockPlan | MockTemplate;
  expanded: boolean;
  onToggle: () => void;
  expandedCreators: Set<string>;
  onToggleCreator: (id: string) => void;
  onEditCreator: (planId: number, creator: MockCreatorNode) => void;
}

function buildPlanTreeRows(
  plan: MockPlan | MockTemplate,
  expanded: boolean,
  expandedCreators: Set<string>,
  onToggle: () => void,
  onToggleCreator: (id: string) => void,
  onEditCreator: (creator: MockCreatorNode) => void,
): SimpleTreeNode[] {
  const rows: SimpleTreeNode[] = [];

  // Root row — plan name
  rows.push({
    id: `plan-${plan.id}`,
    label: plan.name,
    level: 0,
    leaf: false,
    expanded,
    onClick: onToggle,
  });

  if (!expanded) return rows;

  for (const creator of plan.creators) {
    const creatorKey = `plan-${plan.id}-${creator.creatorId}`;
    const hasShapes = creator.shapes.length > 0;
    const creatorExpanded = expandedCreators.has(creatorKey);

    // Creator row
    rows.push({
      id: creatorKey,
      label: creator.creatorId,
      level: 1,
      leaf: !hasShapes,
      expanded: creatorExpanded,
      chip: creator.creatorClassName.replace("Creator", ""),
      onClick: () => onToggleCreator(creatorKey),
      onEdit: () => onEditCreator(creator),
      editTitle: `Edit ${creator.creatorId}`,
    });

    // Input/output shape rows (muted)
    if (hasShapes && creatorExpanded) {
      for (const shape of creator.shapes) {
        rows.push({
          id: `${creatorKey}-${shape.direction}-${shape.name}`,
          label: `${shape.direction === "input" ? "\u2B07" : "\u2B06"} ${shape.name}`,
          level: 2,
          leaf: true,
          muted: true,
          annotation: shape.direction,
        });
      }
    }
  }

  return rows;
}

function PlanTreeSection({
  plan,
  expanded,
  onToggle,
  expandedCreators,
  onToggleCreator,
  onEditCreator,
}: Readonly<PlanTreeSectionProps>) {
  const rows = useMemo(
    () =>
      buildPlanTreeRows(
        plan,
        expanded,
        expandedCreators,
        onToggle,
        onToggleCreator,
        (creator) => onEditCreator(plan.id, creator),
      ),
    [plan, expanded, expandedCreators, onToggle, onToggleCreator, onEditCreator],
  );

  return (
    <div className="flex flex-col">
      {rows.map((node) => (
        <SimpleTreeRow
          key={node.id}
          node={node}
          onToggle={() => {
            if (node.id.startsWith("plan-") && node.level === 0) {
              onToggle();
            } else {
              onToggleCreator(node.id);
            }
          }}
        />
      ))}
    </div>
  );
}

// ── Parameter edit modal ───────────────────────────────────────────

interface EditParamsModalProps {
  open: boolean;
  creator: MockCreatorNode | null;
  creatorInfo: CreatorInfo | null;
  onClose: () => void;
}

function EditParamsModal({ open, creator, creatorInfo, onClose }: Readonly<EditParamsModalProps>) {
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
        <div className="flex max-h-[85vh] w-[520px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl">
          <div className="flex items-center justify-between">
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Edit {creator.creatorId}
            </h2>
            <button
              onClick={onClose}
              className="flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={14} />
            </button>
          </div>

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
                  <span className="font-[family-name:var(--font-jetbrains-mono)]">{s.name}</span>
                  <span className="text-[10px] text-subtle-foreground">({s.direction})</span>
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
              onChange={(key, value) => setValues((prev) => ({ ...prev, [key]: value }))}
              availableShapeKeys={creator.shapes
                .filter((s) => s.direction === "output")
                .map((s) => s.name)}
            />
          ) : (
            <p className="text-[12px] text-muted-foreground">
              Creator &quot;{creator.creatorClassName}&quot; not found in catalog.
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="rounded-full border border-border px-4 py-2 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="rounded-full bg-primary px-4 py-2 text-[12px] text-primary-foreground hover:opacity-90"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}

// ── Template selector ──────────────────────────────────────────────

interface TemplateSelectorProps {
  templates: MockTemplate[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

function TemplateSelector({ templates, selectedId, onSelect }: Readonly<TemplateSelectorProps>) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = templates.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()),
  );
  const selected = templates.find((t) => t.id === selectedId);

  return (
    <div className="relative">
      <div
        className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2 cursor-pointer"
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => { if (e.key === "Enter") setOpen(!open); }}
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
            <p className="px-3 py-2 text-[12px] text-muted-foreground">No templates found</p>
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
                  t.id === selectedId ? "bg-sidebar-accent text-primary" : "text-foreground"
                }`}
              >
                <span className="font-[family-name:var(--font-jetbrains-mono)]">{t.name}</span>
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

// ── Main page ──────────────────────────────────────────────────────

export default function ConstructionPlansPage() {
  const { creators } = useCreators();

  // View mode toggle
  const [viewMode, setViewMode] = useState<"plans" | "templates">("plans");

  // Tree panel width: normal (360px) or wide (2/3 of screen)
  const [treeWide, setTreeWide] = useState(false);

  // Plan mode state
  const [expandedPlans, setExpandedPlans] = useState<Set<number>>(new Set([1, 4, 5]));
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
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const selectedTemplate = MOCK_TEMPLATES.find((t) => t.id === selectedTemplateId) ?? null;
  const [templateExpandedCreators, setTemplateExpandedCreators] = useState<Set<string>>(new Set());

  // Edit modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingCreator, setEditingCreator] = useState<MockCreatorNode | null>(null);

  // Toggle plan expand/collapse
  const togglePlan = useCallback((planId: number) => {
    setExpandedPlans((prev) => {
      const next = new Set(prev);
      if (next.has(planId)) next.delete(planId);
      else next.add(planId);
      return next;
    });
  }, []);

  // Toggle creator expand/collapse
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

  // Open edit modal
  const handleEditCreator = useCallback((_planId: number, creator: MockCreatorNode) => {
    setEditingCreator(creator);
    setEditModalOpen(true);
  }, []);

  // Find matching CreatorInfo for the editing creator
  const editingCreatorInfo = editingCreator
    ? creators.find((c) => c.class_name === editingCreator.creatorClassName) ?? null
    : null;

  // Count all creators recursively
  function countCreators(creators: MockCreatorNode[]): number {
    return creators.reduce(
      (sum, c) => sum + 1 + countCreators(c.successors ?? []),
      0,
    );
  }
  const totalSteps = MOCK_PLANS.reduce((sum, p) => sum + countCreators(p.creators), 0);

  // Render a creator node and its successors recursively
  function renderCreatorTree(
    creator: MockCreatorNode,
    planId: number,
    level: number,
    expandedSet: Set<string>,
    toggleFn: (key: string) => void,
  ) {
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
            onEdit: () => handleEditCreator(planId, creator),
            editTitle: `Edit ${creator.creatorId}`,
            onAdd: () => alert(`Add successor to "${creator.creatorId}"`),
            addTitle: `Add successor to ${creator.creatorId}`,
          }}
          onToggle={() => toggleFn(creatorKey)}
        />

        {hasChildren &&
          isCreatorExpanded && (
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
                renderCreatorTree(successor, planId, level + 1, expandedSet, toggleFn),
              )}
            </>
          )}
      </div>
    );
  }

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
        {/* ─── Left panel: plan/template trees ─── */}
        <div
          className="flex min-h-0 shrink-0 flex-col overflow-hidden transition-all duration-300"
          style={{ width: treeWide ? "66%" : 360, minWidth: treeWide ? "66%" : 360 }}
        >
          <div className="flex h-full flex-col gap-3 overflow-hidden">
          {/* Mode toggle + expand/collapse */}
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
            <button
              onClick={() => setTreeWide((w) => !w)}
              title={treeWide ? "Collapse tree panel" : "Expand tree panel"}
              className="flex size-7 items-center justify-center rounded-xl border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
            >
              {treeWide ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
            </button>
          </div>

          {/* Plan mode */}
          {viewMode === "plans" && (
            <TreeCard
              title="Construction Plans"
              badge={`${totalSteps} steps`}
              actions={
                <button
                  onClick={() => alert("Execute All: would execute all plans")}
                  title="Execute all plans"
                  className="flex items-center gap-1 rounded-full bg-primary px-2.5 py-1 text-[11px] text-primary-foreground hover:opacity-90"
                >
                  <Play size={10} />
                  Execute All
                </button>
              }
            >
              {MOCK_PLANS.map((plan) => (
                <div key={plan.id} className="flex flex-col">
                  {/* Plan header row with action buttons */}
                  <div className="group flex items-center gap-1.5 rounded-xl py-1.5 pr-2 hover:bg-sidebar-accent">
                    <button
                      onClick={() => togglePlan(plan.id)}
                      className="flex items-center"
                    >
                      {expandedPlans.has(plan.id) ? (
                        <ChevronDown size={12} className="shrink-0 text-muted-foreground" />
                      ) : (
                        <ChevronRight size={12} className="shrink-0 text-muted-foreground" />
                      )}
                    </button>
                    <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground font-medium">
                      {plan.name}
                    </span>
                    <span className="flex-1" />
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
                  </div>

                  {/* Creator nodes (when plan is expanded) */}
                  {expandedPlans.has(plan.id) &&
                    plan.creators.map((creator) =>
                      renderCreatorTree(creator, plan.id, 1, expandedCreators, toggleCreator),
                    )}

                  {/* Separator between plans */}
                  <div className="mx-2 my-1 border-b border-border/50" />
                </div>
              ))}
            </TreeCard>
          )}

          {/* Template mode */}
          {viewMode === "templates" && (
            <div className="flex h-full flex-col gap-3 overflow-hidden">
              <TemplateSelector
                templates={MOCK_TEMPLATES}
                selectedId={selectedTemplateId}
                onSelect={(id) => {
                  setSelectedTemplateId(id);
                  // Auto-expand all creators when selecting a template
                  const template = MOCK_TEMPLATES.find((t) => t.id === id);
                  if (template) {
                    setTemplateExpandedCreators(
                      new Set(template.creators.map((c) => `plan-${id}-${c.creatorId}`)),
                    );
                  }
                }}
              />

              {selectedTemplate ? (
                <TreeCard
                  title={selectedTemplate.name}
                  badge={`${selectedTemplate.creators.length} steps`}
                  actions={
                    <button
                      onClick={() => alert("Play Template: would open aeroplane selector")}
                      title="Execute template against an aeroplane"
                      className="flex items-center gap-1 rounded-full bg-primary px-2.5 py-1 text-[11px] text-primary-foreground hover:opacity-90"
                    >
                      <Play size={10} />
                      Test
                    </button>
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
                    renderCreatorTree(creator, selectedTemplate.id, 1, templateExpandedCreators, toggleTemplateCreator),
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
          )}
          </div>
        </div>

        {/* ─── Right panel: Creator Gallery ─── */}
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
