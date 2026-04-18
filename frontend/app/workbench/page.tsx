"use client";

import { useState } from "react";
import { ViewerPanel } from "@/components/workbench/ViewerPanel";
import { ConfigPanel } from "@/components/workbench/ConfigPanel";
import { AeroplaneTree } from "@/components/workbench/AeroplaneTree";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { useWings } from "@/hooks/useWings";
import { usePreviewState } from "@/hooks/usePreviewState";
import { useFuselages } from "@/hooks/useFuselages";

export default function WorkbenchPage() {
  const { aeroplaneId, setAeroplaneId } = useAeroplaneContext();
  const { aeroplanes, isLoading, createAeroplane } = useAeroplanes();
  const { wingNames } = useWings(aeroplaneId);
  const { fuselageNames, mutate: mutateFuselages } = useFuselages(aeroplaneId);
  const preview = usePreviewState(aeroplaneId);
  const aeroplaneName =
    aeroplanes.find((a) => a.id === aeroplaneId)?.name ?? "Aeroplane";

  const [treeOpen, setTreeOpen] = useState(true);
  const [viewerMaximized, setViewerMaximized] = useState(false);

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
    <div className="flex h-full min-h-0 flex-1 gap-4 overflow-hidden">
      {/* Tree Panel — collapsible, fixed width, scrollable */}
      {treeOpen && !viewerMaximized && (
        <div className="flex h-full min-h-0 w-[320px] shrink-0 flex-col overflow-hidden">
          <AeroplaneTree
            aeroplaneId={aeroplaneId}
            wingNames={wingNames}
            fuselageNames={fuselageNames}
            aeroplaneName={aeroplaneName}
            isWingVisible={preview.isWingVisible}
            isWingLoading={(wn) => preview.previews[wn]?.loading ?? false}
            onTogglePreview={preview.toggleWing}
            onToggleAllPreview={preview.toggleAllWings}
            onCollapseTree={() => setTreeOpen(false)}
          />
        </div>
      )}

      {/* Viewer Panel — fills remaining space */}
      <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
        <ViewerPanel
          visibleParts={preview.visibleParts}
          isAnyLoading={preview.isAnyLoading}
          loadingWing={preview.loadingWing}
          isMaximized={viewerMaximized}
          onToggleMaximize={() => setViewerMaximized((m) => !m)}
          isTreeCollapsed={!treeOpen}
          onExpandTree={() => setTreeOpen(true)}
        />
      </div>

      {/* Config Panel — shrinks to content, max 420px */}
      {!viewerMaximized && (
        <div className="flex h-full min-h-0 w-[340px] shrink-0 flex-col overflow-hidden">
          <ConfigPanel
            aeroplaneId={aeroplaneId}
            onGeometryChanged={preview.invalidateWing}
            onFuselageSaved={() => mutateFuselages()}
          />
        </div>
      )}
    </div>
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
