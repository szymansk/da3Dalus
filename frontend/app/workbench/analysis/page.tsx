"use client";

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAnalysis } from "@/hooks/useAnalysis";
import { AnalysisViewerPanel } from "@/components/workbench/AnalysisViewerPanel";
import { AnalysisConfigPanel } from "@/components/workbench/AnalysisConfigPanel";

export default function AnalysisPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const analysis = useAnalysis(aeroplaneId);

  return (
    <>
      <AnalysisViewerPanel result={analysis.result} aeroplaneId={aeroplaneId} />
      <AnalysisConfigPanel analysis={analysis} />
    </>
  );
}
