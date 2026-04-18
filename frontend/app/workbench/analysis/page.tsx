"use client";

import { Group, Panel } from "react-resizable-panels";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAnalysis } from "@/hooks/useAnalysis";
import { AnalysisViewerPanel } from "@/components/workbench/AnalysisViewerPanel";
import { AnalysisConfigPanel } from "@/components/workbench/AnalysisConfigPanel";
import { SplitHandle } from "@/components/workbench/SplitHandle";

export default function AnalysisPage() {
  const { aeroplaneId } = useAeroplaneContext();
  const analysis = useAnalysis(aeroplaneId);

  return (
    <Group orientation="horizontal" className="h-full min-h-0 flex-1">
      <Panel defaultSize={55} minSize={20}>
        <AnalysisViewerPanel
          result={analysis.result}
          aeroplaneId={aeroplaneId}
          lastRunTime={analysis.lastRunTime}
          lastRunDurationMs={analysis.lastRunDurationMs}
        />
      </Panel>
      <SplitHandle />
      <Panel defaultSize={45} minSize={25}>
        <AnalysisConfigPanel analysis={analysis} />
      </Panel>
    </Group>
  );
}
