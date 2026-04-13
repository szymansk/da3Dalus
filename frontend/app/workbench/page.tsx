"use client";

import { Group, Panel, Separator } from "react-resizable-panels";
import { ViewerPanel } from "@/components/workbench/ViewerPanel";
import { ConfigPanel } from "@/components/workbench/ConfigPanel";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { usePreviewState } from "@/hooks/usePreviewState";

export default function WorkbenchPage() {
  const { aeroplaneId, setAeroplaneId } = useAeroplaneContext();
  const { aeroplanes, isLoading, createAeroplane } = useAeroplanes();
  const preview = usePreviewState(aeroplaneId);

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
    <Group orientation="horizontal" className="flex-1">
      <Panel defaultSize={55} minSize={20}>
        <ViewerPanel
          visibleParts={preview.getVisibleParts()}
          isAnyLoading={preview.isAnyLoading}
          loadingWing={preview.loadingWing}
        />
      </Panel>
      <Separator className="w-1.5 bg-border hover:bg-primary/50 transition-colors cursor-col-resize" />
      <Panel defaultSize={45} minSize={30}>
        <ConfigPanel
          aeroplaneId={aeroplaneId}
          isWingVisible={preview.isWingVisible}
          isWingLoading={(wn) => preview.previews[wn]?.loading ?? false}
          onTogglePreview={preview.toggleWing}
          onGeometryChanged={preview.invalidateWing}
        />
      </Panel>
    </Group>
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
      <div className="flex w-[400px] flex-col gap-4 rounded-[--radius-m] border border-border bg-card p-6">
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
                className="flex items-center justify-between rounded-[--radius-s] px-3 py-2.5 text-left hover:bg-sidebar-accent"
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
          className="rounded-[--radius-pill] bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90"
        >
          + Create New
        </button>
      </div>
    </div>
  );
}
