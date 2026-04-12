import { AnalysisViewerPanel } from "@/components/workbench/AnalysisViewerPanel";
import { AnalysisConfigPanel } from "@/components/workbench/AnalysisConfigPanel";

export default function AnalysisPage() {
  return (
    <>
      <AnalysisViewerPanel />
      <AnalysisConfigPanel />
    </>
  );
}
