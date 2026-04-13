"use client";

import { useState, useCallback } from "react";
import { Box, Loader, RefreshCw, Layers } from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { CadViewer } from "./CadViewer";
import { useTessellation } from "@/hooks/useTessellation";
import { useWings } from "@/hooks/useWings";
import { API_BASE } from "@/lib/fetcher";

const STAGES = ["Bare Aero", "+TEDs", "+Spars", "Final Print"] as const;
type Stage = (typeof STAGES)[number];

export function ViewerPanel() {
  const [activeStage, setActiveStage] = useState<Stage>("Bare Aero");
  const { aeroplaneId, selectedWing } = useAeroplaneContext();
  const { data, isTessellating, progress, error, triggerTessellation } =
    useTessellation(aeroplaneId, selectedWing);
  const { wingNames } = useWings(aeroplaneId);

  // "Preview All" — tessellate each wing sequentially, then load assembled scene
  const [allProgress, setAllProgress] = useState("");
  const [allData, setAllData] = useState<Record<string, unknown> | null>(null);
  const isTessellatingAll = !!allProgress;

  const triggerAllTessellation = useCallback(async () => {
    if (!aeroplaneId || wingNames.length === 0) return;
    setAllData(null);

    for (let i = 0; i < wingNames.length; i++) {
      const wn = wingNames[i];
      setAllProgress(`Tessellating ${wn} (${i + 1}/${wingNames.length})…`);
      try {
        const postRes = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(wn)}/tessellation`,
          { method: "POST" },
        );
        if (!postRes.ok) continue;

        // Poll until done
        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
          const r = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/status?task_type=tessellation&wing_name=${encodeURIComponent(wn)}`);
          const s = await r.json();
          if (s.status === "SUCCESS") break;
          if (s.status === "FAILURE") break;
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
      } catch { /* continue with next wing */ }
    }

    // Load assembled scene
    setAllProgress("Loading assembled scene…");
    try {
      const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/tessellation`);
      if (res.ok) {
        setAllData(await res.json());
      }
    } catch { /* ignore */ }
    setAllProgress("");
  }, [aeroplaneId, wingNames]);

  const viewerData = allData ?? data;

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-[--radius-m] border border-border">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          CAD Viewer
        </span>
        {viewerData && !isTessellating && !isTessellatingAll && (
          <button
            onClick={selectedWing ? triggerTessellation : triggerAllTessellation}
            className="flex items-center gap-1 rounded-[--radius-s] border border-border bg-card-muted px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
            title="Re-tessellate"
          >
            <RefreshCw size={11} />
            Refresh
          </button>
        )}
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {STAGES.map((stage) => (
            <button
              key={stage}
              onClick={() => setActiveStage(stage)}
              className={`rounded-[--radius-pill] px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
                stage === activeStage
                  ? "bg-primary text-primary-foreground"
                  : "bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
              }`}
            >
              {stage}
            </button>
          ))}
        </div>
      </div>

      {/* Viewer Body */}
      <div className="flex flex-1 flex-col bg-card-muted">
        {viewerData ? (
          <CadViewer data={viewerData} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6">
            <Box size={72} className="text-subtle-foreground" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
              {selectedWing
                ? `Click "Preview" to render ${selectedWing}`
                : wingNames.length > 0
                  ? "Preview individual wing or all wings"
                  : "Select a wing to preview"}
            </span>
            <div className="flex gap-2">
              {selectedWing && (
                <button
                  onClick={triggerTessellation}
                  disabled={isTessellating || isTessellatingAll}
                  className="rounded-[--radius-pill] bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
                >
                  {isTessellating ? "Tessellating…" : "Preview 3D"}
                </button>
              )}
              {wingNames.length > 0 && (
                <button
                  onClick={triggerAllTessellation}
                  disabled={isTessellating || isTessellatingAll}
                  className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted border border-border px-4 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
                >
                  <Layers size={14} />
                  {isTessellatingAll ? "Tessellating…" : "Preview All"}
                </button>
              )}
            </div>
            {error && (
              <span className="max-w-md text-center text-[12px] text-destructive">{error}</span>
            )}
          </div>
        )}
      </div>

      {/* Task Toast */}
      {(isTessellating || isTessellatingAll) && (
        <div className="flex items-center gap-3 border-t border-border bg-card px-4 py-3">
          <Loader size={14} className="animate-spin text-primary" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
            {allProgress || progress}
          </span>
        </div>
      )}
    </div>
  );
}
