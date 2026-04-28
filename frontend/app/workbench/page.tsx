"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import { PanelLeftOpen, Maximize2, Minimize2, X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { PropertyForm, type PropertyFormHandle } from "@/components/workbench/PropertyForm";
import { SegmentPaginator } from "@/components/workbench/SegmentPaginator";
import { useWingConfig } from "@/hooks/useWingConfig";
import { AeroplaneTree } from "@/components/workbench/AeroplaneTree";
import { SparEditDialog } from "@/components/workbench/SparEditDialog";
import { TedEditDialog } from "@/components/workbench/TedEditDialog";
import { WingOutlineViewer } from "@/components/workbench/WingOutlineViewer";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { useWings, useWing, useAllWingData } from "@/hooks/useWings";
import { useFuselages } from "@/hooks/useFuselages";
import { useAllFuselageData, useFuselage } from "@/hooks/useFuselage";
import { API_BASE } from "@/lib/fetcher";

export default function WorkbenchPage() {
  const {
    aeroplaneId, setAeroplaneId,
    selectedWing, selectedXsecIndex, selectXsec,
    selectedFuselage, selectedFuselageXsecIndex, selectFuselageXsec,
    treeMode,
  } = useAeroplaneContext();
  const { aeroplanes, isLoading, createAeroplane } = useAeroplanes();
  const { wingNames, mutate: mutateWingNames } = useWings(aeroplaneId);
  const { fuselageNames, mutate: mutateFuselages } = useFuselages(aeroplaneId);
  const { wing, mutate: mutateSelectedWing } = useWing(aeroplaneId, selectedWing);
  const { wingConfig } = useWingConfig(aeroplaneId, treeMode === "wingconfig" ? selectedWing : null);
  const { fuselage } = useFuselage(aeroplaneId, treeMode === "fuselage" ? selectedFuselage : null);

  const mode = treeMode === "fuselage" ? "fuselage" : treeMode;

  const paginatorCurrent = mode === "fuselage"
    ? selectedFuselageXsecIndex
    : selectedXsecIndex;

  const paginatorTotal = mode === "fuselage"
    ? fuselage?.x_secs?.length
    : mode === "wingconfig"
      ? wingConfig?.segments?.length
      : wing?.x_secs?.length;

  const formRef = useRef<PropertyFormHandle>(null);

  const handleSegmentChange = useCallback(async (newIndex: number) => {
    if (formRef.current) {
      try {
        await formRef.current.save();
      } catch {
        return;
      }
    }
    if (mode === "fuselage") {
      selectFuselageXsec(newIndex);
    } else {
      selectXsec(newIndex);
    }
  }, [mode, selectXsec, selectFuselageXsec]);

  const aeroplaneName =
    aeroplanes.find((a) => a.id === aeroplaneId)?.name ?? "Aeroplane";

  const [treeOpen, setTreeOpen] = useState(true);
  const [viewerMaximized, setViewerMaximized] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const { dialogRef: configDialogRef, handleClose: configHandleClose } = useDialog(configOpen, () => setConfigOpen(false));

  // Spar/TED dialog state
  const [sparDialog, setSparDialog] = useState<{
    wingName: string; xsecIndex: number; sparIndex?: number; data?: Record<string, unknown>;
  } | null>(null);
  const [tedDialog, setTedDialog] = useState<{
    wingName: string; xsecIndex: number; isNew: boolean; data?: Record<string, unknown>;
  } | null>(null);

  // Visibility: all wings/fuselages visible by default
  const [visibleWings, setVisibleWings] = useState<Set<string>>(new Set());
  const [visibleFuselages, setVisibleFuselages] = useState<Set<string>>(new Set());

  // Auto-add new wings/fuselages to visible set
  const effectiveVisibleWings = useMemo(() => {
    const s = new Set(visibleWings);
    for (const wn of wingNames) {
      if (!visibleWings.has(wn) && !visibleWings.has(`_hidden_${wn}`)) s.add(wn);
    }
    return s;
  }, [wingNames, visibleWings]);

  const effectiveVisibleFuselages = useMemo(() => {
    const s = new Set(visibleFuselages);
    for (const fn of fuselageNames) {
      if (!visibleFuselages.has(fn) && !visibleFuselages.has(`_hidden_${fn}`)) s.add(fn);
    }
    return s;
  }, [fuselageNames, visibleFuselages]);

  function toggleWingVisibility(name: string) {
    setVisibleWings((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
        next.add(`_hidden_${name}`);
      } else {
        next.add(name);
        next.delete(`_hidden_${name}`);
      }
      return next;
    });
  }

  function toggleFuselageVisibility(name: string) {
    setVisibleFuselages((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
        next.add(`_hidden_${name}`);
      } else {
        next.add(name);
        next.delete(`_hidden_${name}`);
      }
      return next;
    });
  }

  function toggleAllWings(names: string[]) {
    const allVisible = names.every((n) => effectiveVisibleWings.has(n));
    setVisibleWings((prev) => {
      const next = new Set(prev);
      for (const n of names) {
        if (allVisible) {
          next.delete(n);
          next.add(`_hidden_${n}`);
        } else {
          next.add(n);
          next.delete(`_hidden_${n}`);
        }
      }
      return next;
    });
  }

  // Load all wing/fuselage data for the wireframe viewer
  const { wings: allWings, mutate: mutateAllWings } = useAllWingData(aeroplaneId, wingNames);
  const { fuselages: allFuselages, mutate: mutateAllFuselages } = useAllFuselageData(aeroplaneId, fuselageNames);

  if (!aeroplaneId) {
    return <AeroplaneSelector
      aeroplanes={aeroplanes}
      isLoading={isLoading}
      onSelect={setAeroplaneId}
      onCreate={async (name: string) => {
        const created = await createAeroplane(name);
        setAeroplaneId(created.id);
      }}
    />;
  }

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
        {/* Tree Panel — collapsible, fixed width, scrollable */}
        {treeOpen && !viewerMaximized && (
          <div className="flex h-full min-h-0 w-[320px] shrink-0 flex-col overflow-hidden">
            <AeroplaneTree
              aeroplaneId={aeroplaneId}
              wingNames={wingNames}
              fuselageNames={fuselageNames}
              aeroplaneName={aeroplaneName}
              isWingVisible={(wn) => effectiveVisibleWings.has(wn)}
              onTogglePreview={toggleWingVisibility}
              onToggleAllPreview={toggleAllWings}
              isFuselageVisible={(fn) => effectiveVisibleFuselages.has(fn)}
              onToggleFuselagePreview={toggleFuselageVisibility}
              onCollapseTree={() => setTreeOpen(false)}
              onNodeEdit={() => setConfigOpen(true)}
              onWingSaved={() => { mutateWingNames(); mutateAllWings(); }}
              onFuselageSaved={() => { mutateFuselages(); mutateAllFuselages(); }}
              onEditSpar={(wn, xi, si, data) => setSparDialog({ wingName: wn, xsecIndex: xi, sparIndex: si, data })}
              onDeleteSpar={async (wn, xi, si) => {
                if (!aeroplaneId) return;
                const res = await fetch(
                  `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wn}/cross_sections/${xi}/spars/${si}`,
                  { method: "DELETE" },
                );
                if (res.ok) { mutateSelectedWing(); mutateAllWings(); }
              }}
              onEditTed={(wn, xi, data) => setTedDialog({ wingName: wn, xsecIndex: xi, isNew: false, data })}
              onDeleteTed={async (wn, xi) => {
                if (!aeroplaneId) return;
                const res = await fetch(
                  `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wn}/cross_sections/${xi}/control_surface`,
                  { method: "DELETE" },
                );
                if (res.ok) { mutateSelectedWing(); mutateAllWings(); }
              }}
              onAddSpar={(wn, xi) => setSparDialog({ wingName: wn, xsecIndex: xi })}
              onAddTed={(wn, xi) => setTedDialog({ wingName: wn, xsecIndex: xi, isNew: true })}
            />
          </div>
        )}

        {/* Plotly Wireframe Viewer — fills remaining space */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-border">
          <div className="flex shrink-0 items-center gap-2 border-b border-border bg-card px-4 py-3">
            {!treeOpen && (
              <button
                onClick={() => setTreeOpen(true)}
                className="flex size-6 items-center justify-center rounded-xl text-muted-foreground hover:bg-sidebar-accent"
                title="Show tree panel"
              >
                <PanelLeftOpen size={14} />
              </button>
            )}
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
              Preview
            </span>
            <div className="flex-1" />
            <button
              onClick={() => setViewerMaximized((m) => !m)}
              className="flex size-8 items-center justify-center rounded-xl border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
              title={viewerMaximized ? "Restore panels" : "Maximize viewer"}
            >
              {viewerMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          </div>
          <div className="min-h-0 flex-1">
            <WingOutlineViewer
              wings={allWings}
              fuselages={allFuselages}
              visibleWings={effectiveVisibleWings}
              visibleFuselages={effectiveVisibleFuselages}
              selectedWing={selectedWing}
              selectedXsecIndex={selectedXsecIndex}
              selectedFuselage={selectedFuselage}
              selectedFuselageXsecIndex={selectedFuselageXsecIndex}
            />
          </div>
        </div>
      </div>

      {/* Configuration Modal — opens via pencil icon on segments/xsecs */}
      <dialog
        ref={configDialogRef}
        className="m-auto bg-transparent backdrop:bg-black/60"
        onClose={configHandleClose}
        aria-label="Configuration"
      >
        {configOpen && (
          <div className="flex max-h-[85vh] w-[480px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                Configuration
              </h2>
              {paginatorCurrent != null && paginatorTotal != null && paginatorTotal > 1 && (
                <SegmentPaginator
                  current={paginatorCurrent}
                  total={paginatorTotal}
                  onChange={handleSegmentChange}
                />
              )}
              <button
                aria-label="Close"
                onClick={() => setConfigOpen(false)}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>
            <PropertyForm ref={formRef} onGeometryChanged={() => { mutateAllWings(); mutateSelectedWing(); mutateAllFuselages(); }} />
          </div>
        )}
      </dialog>

      {/* Spar Edit/Add Dialog */}
      {sparDialog && aeroplaneId && (
        <SparEditDialog
          open
          onClose={() => setSparDialog(null)}
          aeroplaneId={aeroplaneId}
          wingName={sparDialog.wingName}
          xsecIndex={sparDialog.xsecIndex}
          sparIndex={sparDialog.sparIndex}
          initialData={sparDialog.data as {
            spare_position_factor: number;
            spare_support_dimension_width: number;
            spare_support_dimension_height: number;
            spare_mode: string;
            spare_start: number;
            spare_length?: number;
          }}
          onSaved={() => { mutateSelectedWing(); mutateAllWings(); }}
        />
      )}

      {/* TED Edit/Add Dialog */}
      {tedDialog && aeroplaneId && (
        <TedEditDialog
          open
          onClose={() => setTedDialog(null)}
          aeroplaneId={aeroplaneId}
          wingName={tedDialog.wingName}
          xsecIndex={tedDialog.xsecIndex}
          isNew={tedDialog.isNew}
          initialData={tedDialog.data}
          onSaved={() => { mutateSelectedWing(); mutateAllWings(); }}
        />
      )}
    </>
  );
}

function AeroplaneSelector({
  aeroplanes,
  isLoading,
  onSelect,
  onCreate,
}: Readonly<{
  aeroplanes: { id: string; name: string; created_at: string; updated_at: string }[];
  isLoading: boolean;
  onSelect: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
}>) {
  async function handleCreate() {
    const name = prompt("Aeroplane name?");
    if (!name) return;
    await onCreate(name);
  }

  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="flex w-[400px] flex-col gap-4 rounded-xl border border-border bg-card p-6">
        <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
          Select Aeroplane
        </h2>

        {isLoading && (
          <span className="text-[13px] text-muted-foreground">Loading...</span>
        )}
        {!isLoading && aeroplanes.length === 0 && (
          <span className="text-[13px] text-muted-foreground">
            No aeroplanes yet. Create one to get started.
          </span>
        )}
        {!isLoading && aeroplanes.length > 0 && (
          <div className="flex flex-col gap-1">
            {aeroplanes.map((a) => (
              <button
                key={a.id}
                onClick={() => onSelect(a.id)}
                className="flex items-center justify-between rounded-xl px-3 py-2.5 text-left hover:bg-sidebar-accent"
              >
                <span className="text-[13px] text-foreground">{a.name}</span>
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                  {new Date(a.updated_at).toLocaleDateString()}
                </span>
              </button>
            ))}
          </div>
        )}

        <button
          onClick={handleCreate}
          className="rounded-full bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90"
        >
          + Create New
        </button>
      </div>
    </div>
  );
}
