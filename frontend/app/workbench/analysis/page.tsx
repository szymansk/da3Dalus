"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAnalysis } from "@/hooks/useAnalysis";
import { useStripForces } from "@/hooks/useStripForces";
import { useStreamlines } from "@/hooks/useStreamlines";
import { useWings, useWing } from "@/hooks/useWings";
import { AnalysisViewerPanel, type Tab } from "@/components/workbench/AnalysisViewerPanel";
import { AnalysisConfigPanel } from "@/components/workbench/AnalysisConfigPanel";

export default function AnalysisPage() {
  const { aeroplaneId, selectedWing } = useAeroplaneContext();
  const analysis = useAnalysis(aeroplaneId);
  const stripForces = useStripForces(aeroplaneId);
  const streamlines = useStreamlines(aeroplaneId);
  const { wingNames } = useWings(aeroplaneId);
  const { wing } = useWing(aeroplaneId, selectedWing ?? wingNames[0] ?? null);
  const [configOpen, setConfigOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("Polar");
  const { dialogRef, handleClose: dialogHandleClose } = useDialog(configOpen, () => setConfigOpen(false));

  const modalTitleByTab: Record<Tab, string> = {
    "Polar": "Polar Configuration",
    "Trefftz Plane": "Trefftz Plane Configuration",
    "Streamlines": "Streamlines Configuration",
  };
  const modalTitle = modalTitleByTab[activeTab];

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
        {/* Viewer fills remaining space */}
        <div className="min-h-0 flex-1 overflow-hidden">
          <AnalysisViewerPanel
            result={analysis.result}
            aeroplaneId={aeroplaneId}
            lastRunTime={analysis.lastRunTime}
            lastRunDurationMs={analysis.lastRunDurationMs}
            stripForces={stripForces.result}
            stripForcesLoading={stripForces.isRunning}
            streamlinesFigure={streamlines.figure}
            streamlinesLoading={streamlines.isComputing}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onConfigureClick={() => setConfigOpen(true)}
            wingXSecs={wing?.x_secs}
            wingSymmetric={wing?.symmetric}
          />
        </div>
      </div>

      {/* Config Modal */}
      <dialog
        ref={dialogRef}
        role="dialog"
        className="fixed inset-0 z-50 flex items-center justify-center bg-transparent backdrop:bg-black/60"
        onClose={dialogHandleClose}
        onClick={(e) => { if (e.target === e.currentTarget) dialogHandleClose(); }}
        onKeyDown={(e) => { if (e.key === "Escape") dialogHandleClose(); }}
        aria-label={modalTitle}
      >
        {configOpen && (
          <div className="flex max-h-[85vh] w-[480px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                {modalTitle}
              </h2>
              <button
                onClick={() => setConfigOpen(false)}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>
            <AnalysisConfigPanel
              activeTab={activeTab}
              analysis={analysis}
              wingNames={wingNames}
              selectedWing={selectedWing ?? null}
              onRunStripForces={(params) => {
                stripForces.runAll(params);
              }}
              stripForcesRunning={stripForces.isRunning}
              stripForcesError={stripForces.error}
              onRunStreamlines={(params) => {
                streamlines.computeStreamlines(params);
              }}
              streamlinesRunning={streamlines.isComputing}
              streamlinesError={streamlines.error}
              onClose={() => setConfigOpen(false)}
            />
          </div>
        )}
      </dialog>
    </>
  );
}
