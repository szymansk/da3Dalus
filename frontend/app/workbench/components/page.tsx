"use client";

import { useState } from "react";
import { Package, Search, Plus, Settings, Trash2, Box } from "lucide-react";
import { PillToggle, type PillToggleOption } from "@/components/ui/PillToggle";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { ComponentTree } from "@/components/workbench/ComponentTree";
import { ComponentEditDialog } from "@/components/workbench/ComponentEditDialog";
import { ConstructionPartsGrid } from "@/components/workbench/ConstructionPartsGrid";
import { ConstructionPartUploadDialog } from "@/components/workbench/ConstructionPartUploadDialog";
import { NodePropertyPanel } from "@/components/workbench/NodePropertyPanel";
import { ComponentTypeManagementDialog } from "@/components/workbench/ComponentTypeManagementDialog";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useComponents, deleteComponent, type Component } from "@/hooks/useComponents";
import {
  useComponentTree,
  type ComponentTreeNode,
} from "@/hooks/useComponentTree";
import { useConstructionParts } from "@/hooks/useConstructionParts";
import { findNode } from "@/lib/treeDnd";

type View = "library" | "construction";

const TYPE_ICONS: Record<string, string> = {
  servo: "\u2699",
  brushless_motor: "\u26A1",
  esc: "\u26A1",
  battery: "\uD83D\uDD0B",
  receiver: "\uD83D\uDCE1",
  flight_controller: "\uD83D\uDDA5",
  material: "\uD83E\uDDF1",
  propeller: "\uD83D\uDCA8",
  generic: "\uD83D\uDCE6",
};

export default function ComponentsPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const [view, setView] = useState<View>("library");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const { components, total, isLoading, mutate } = useComponents(typeFilter || undefined, search || undefined);
  const [editDialog, setEditDialog] = useState<{ open: boolean; component: Component | null }>({ open: false, component: null });
  const [typesDialog, setTypesDialog] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const { mutate: mutateParts } = useConstructionParts(aeroplaneId);

  // The pencil icon on each tree row opens a property-edit modal. We keep
  // only the node ID so the modal re-reads fresh data from the SWR tree
  // snapshot after every mutate (save / delete / lock / move).
  const [editingNodeId, setEditingNodeId] = useState<number | null>(null);
  const { tree, mutate: mutateTree } = useComponentTree(aeroplaneId);
  const editingNode = editingNodeId == null ? null : findNode(tree, editingNodeId);

  const viewOptions: PillToggleOption<View>[] = [
    { value: "library", label: "Library", icon: Package },
    { value: "construction", label: "Construction Parts", icon: Box },
  ];

  const handleDelete = async (comp: Component) => {
    if (!confirm(`Delete "${comp.name}"?`)) return;
    try {
      await deleteComponent(comp.id);
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <>
    <WorkbenchTwoPanel>
      <div className="flex h-full flex-col gap-3 overflow-hidden">
        <PillToggle options={viewOptions} value={view} onChange={setView} />
        <ComponentTree
          onNodeEditRequested={(n: ComponentTreeNode) => setEditingNodeId(n.id)}
        />
      </div>

      <div className="flex min-h-0 w-full flex-1 flex-col gap-4 overflow-y-auto">
        {view === "construction" && aeroplaneId && (
          <ConstructionPartsGrid
            aeroplaneId={aeroplaneId}
            onRequestUpload={() => setUploadOpen(true)}
          />
        )}
        {view === "construction" && !aeroplaneId && (
          <p className="py-8 text-center text-[13px] text-muted-foreground">
            Select an aeroplane first.
          </p>
        )}
        {view !== "construction" && (
        <>
        {/* Header */}
        <div className="flex items-center gap-2.5">
          <Package className="size-5 text-primary" />
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
            Component Library
          </h1>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
            {total} items
          </span>
          <span className="flex-1" />
          <button
            onClick={() => setTypesDialog(true)}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-2 text-[13px] text-foreground hover:bg-sidebar-accent"
            title="Manage component types"
          >
            <Settings size={14} />
            Manage Types
          </button>
          <button
            onClick={() => setEditDialog({ open: true, component: null })}
            className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90"
          >
            <Plus size={14} />
            New Component
          </button>
        </div>

        {/* Search + Filter */}
        <div className="flex gap-3">
          <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
            <Search className="size-3.5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search components..."
              className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground"
          >
            <option value="">All types</option>
            <option value="servo">Servo</option>
            <option value="brushless_motor">Motor</option>
            <option value="esc">ESC</option>
            <option value="battery">Battery</option>
            <option value="receiver">Receiver</option>
            <option value="flight_controller">Flight Controller</option>
            <option value="material">Material</option>
            <option value="propeller">Propeller</option>
            <option value="generic">Generic</option>
          </select>
        </div>

        {/* Component Cards */}
        {isLoading && (
          <p className="py-8 text-center text-[13px] text-muted-foreground">Loading components...</p>
        )}
        {!isLoading && components.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-12">
            <Package className="size-12 text-subtle-foreground" />
            <p className="text-[13px] text-muted-foreground">
              {search || typeFilter ? "No components match your filter" : "No components yet. Create one to get started."}
            </p>
          </div>
        )}
        {!isLoading && components.length > 0 && (
          <div className="grid grid-cols-2 gap-3">
            {components.map((comp) => (
              <div
                key={comp.id}
                className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[16px]">{TYPE_ICONS[comp.component_type] ?? "\uD83D\uDCE6"}</span>
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                    {comp.name}
                  </span>
                  <span className="flex-1" />
                  <span className="rounded-full bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
                    {comp.component_type}
                  </span>
                </div>

                {comp.manufacturer && (
                  <span className="text-[11px] text-muted-foreground">{comp.manufacturer}</span>
                )}
                {comp.description && (
                  <span className="text-[11px] text-subtle-foreground">{comp.description}</span>
                )}

                <div className="flex items-center gap-3 text-[11px]">
                  {comp.mass_g != null && (
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-foreground">
                      {comp.mass_g}g
                    </span>
                  )}
                  {comp.bbox_x_mm != null && (
                    <span className="text-muted-foreground">
                      {comp.bbox_x_mm}×{comp.bbox_y_mm}×{comp.bbox_z_mm}mm
                    </span>
                  )}
                </div>

                {/* Specs */}
                {Object.keys(comp.specs).length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(comp.specs).slice(0, 4).map(([key, val]) => (
                      <span key={key} className="rounded-full bg-card-muted px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
                        {key}: {String(val)}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex justify-end gap-1.5">
                  <button
                    onClick={() => setEditDialog({ open: true, component: comp })}
                    className="flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                    title="Edit"
                  >
                    <Settings size={12} />
                  </button>
                  <button
                    onClick={() => handleDelete(comp)}
                    className="flex size-7 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20"
                    title="Delete"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </>
        )}
      </div>
    </WorkbenchTwoPanel>

    {/*
     * Dialog must render as a sibling of <WorkbenchTwoPanel/>, not as a
     * child — WorkbenchTwoPanel only renders its first two children and
     * silently drops the rest. See gh#57-fav regression tests.
     */}
    {editDialog.open && (
      <ComponentEditDialog
        open={editDialog.open}
        onClose={() => setEditDialog({ open: false, component: null })}
        onSaved={() => mutate()}
        component={editDialog.component}
      />
    )}

    {uploadOpen && aeroplaneId && (
      <ConstructionPartUploadDialog
        open={uploadOpen}
        aeroplaneId={aeroplaneId}
        onClose={() => setUploadOpen(false)}
        onSaved={() => mutateParts()}
      />
    )}

    {editingNode && aeroplaneId && (
      <NodePropertyPanel
        node={editingNode}
        aeroplaneId={aeroplaneId}
        onMutate={() => mutateTree()}
        onClose={() => setEditingNodeId(null)}
      />
    )}

    <ComponentTypeManagementDialog
      open={typesDialog}
      onClose={() => setTypesDialog(false)}
    />
    </>
  );
}
