"use client";

import { useState, useMemo } from "react";
import { X, PanelLeftOpen, Maximize2, Minimize2 } from "lucide-react";
import { PropertyForm } from "@/components/workbench/PropertyForm";
import { AeroplaneTree } from "@/components/workbench/AeroplaneTree";
import { WingOutlineViewer } from "@/components/workbench/WingOutlineViewer";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { useWings, useWing, type Wing } from "@/hooks/useWings";
import { useFuselages } from "@/hooks/useFuselages";
import { useFuselage, type Fuselage } from "@/hooks/useFuselage";

export default function WorkbenchPage() {
  const { aeroplaneId, setAeroplaneId } = useAeroplaneContext();
  const { aeroplanes, isLoading, createAeroplane } = useAeroplanes();
  const { wingNames } = useWings(aeroplaneId);
  const { fuselageNames, mutate: mutateFuselages } = useFuselages(aeroplaneId);
  const aeroplaneName =
    aeroplanes.find((a) => a.id === aeroplaneId)?.name ?? "Aeroplane";

  const [treeOpen, setTreeOpen] = useState(true);
  const [viewerMaximized, setViewerMaximized] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);

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

  // Load wing/fuselage data for visible items
  // Note: hooks can't be called conditionally, so we load the first wing/fuselage
  // For multiple wings, we'd need a bulk hook — for now use the selected wing
  const { wing: firstWing } = useWing(aeroplaneId, wingNames[0] ?? null);
  const { wing: secondWing } = useWing(aeroplaneId, wingNames[1] ?? null);
  const { wing: thirdWing } = useWing(aeroplaneId, wingNames[2] ?? null);
  const { fuselage: firstFuselage } = useFuselage(aeroplaneId, fuselageNames[0] ?? null);
  const { fuselage: secondFuselage } = useFuselage(aeroplaneId, fuselageNames[1] ?? null);

  const allWings: Wing[] = useMemo(() => {
    const wings: Wing[] = [];
    if (firstWing) wings.push(firstWing);
    if (secondWing) wings.push(secondWing);
    if (thirdWing) wings.push(thirdWing);
    return wings;
  }, [firstWing, secondWing, thirdWing]);

  const allFuselages: Fuselage[] = useMemo(() => {
    const fuses: Fuselage[] = [];
    if (firstFuselage) fuses.push(firstFuselage);
    if (secondFuselage) fuses.push(secondFuselage);
    return fuses;
  }, [firstFuselage, secondFuselage]);

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
              onCollapseTree={() => setTreeOpen(false)}
              onNodeEdit={() => setConfigOpen(true)}
              onFuselageSaved={() => mutateFuselages()}
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
            />
          </div>
        </div>
      </div>

      {/* Configuration Modal */}
      {configOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setConfigOpen(false)}
        >
          <div
            className="flex max-h-[85vh] w-[480px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                Configuration
              </h2>
              <button
                onClick={() => setConfigOpen(false)}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>
            <PropertyForm />
          </div>
        </div>
      )}
    </>
  );
}

function AeroplaneSelector({
  aeroplanes,
  isLoading,
  onSelect,
  onCreate,
}: {
  aeroplanes: { id: string; name: string; created_at: string; updated_at: string }[];
  isLoading: boolean;
  onSelect: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
}) {
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

        {isLoading ? (
          <span className="text-[13px] text-muted-foreground">Loading...</span>
        ) : aeroplanes.length === 0 ? (
          <span className="text-[13px] text-muted-foreground">
            No aeroplanes yet. Create one to get started.
          </span>
        ) : (
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
