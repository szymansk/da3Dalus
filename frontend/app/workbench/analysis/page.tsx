"use client";

import { useState } from "react";
import { Settings, X } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAnalysis } from "@/hooks/useAnalysis";
import { AnalysisViewerPanel } from "@/components/workbench/AnalysisViewerPanel";
import { AnalysisConfigPanel } from "@/components/workbench/AnalysisConfigPanel";

export default function AnalysisPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const analysis = useAnalysis(aeroplaneId);
  const [configOpen, setConfigOpen] = useState(false);

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
        {/* Config button */}
        <div className="flex shrink-0 items-center justify-end px-2 py-1">
          <button
            onClick={() => setConfigOpen(true)}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
          >
            <Settings size={12} />
            Configure & Run
          </button>
        </div>
        {/* Viewer fills remaining space */}
        <div className="min-h-0 flex-1 overflow-hidden">
          <AnalysisViewerPanel
            result={analysis.result}
            aeroplaneId={aeroplaneId}
            lastRunTime={analysis.lastRunTime}
            lastRunDurationMs={analysis.lastRunDurationMs}
          />
        </div>
      </div>

      {/* Config Modal */}
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
                Analysis Configuration
              </h2>
              <button
                onClick={() => setConfigOpen(false)}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>
            <AnalysisConfigPanel analysis={analysis} />
          </div>
        </div>
      )}
    </>
  );
}
