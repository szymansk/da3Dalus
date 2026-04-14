"use client";

import { useState, useEffect } from "react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWingConfig } from "@/hooks/useWingConfig";
import { useAirfoilGeometry } from "@/hooks/useAirfoilGeometry";
import { useAirfoilAnalysis } from "@/hooks/useAirfoilAnalysis";
import { AirfoilPreviewViewerPanel } from "@/components/workbench/AirfoilPreviewViewerPanel";
import { AirfoilPreviewConfigPanel } from "@/components/workbench/AirfoilPreviewConfigPanel";

/** Extract short airfoil name from path like "./components/airfoils/mh32.dat" */
function airfoilShortName(raw: string): string {
  return (raw.split("/").pop() ?? raw).replace(/\.dat$/i, "");
}

export default function AirfoilPreviewPage() {
  const { aeroplaneId, selectedWing, selectedXsecIndex } =
    useAeroplaneContext();
  const { wingConfig } = useWingConfig(aeroplaneId, selectedWing);

  const segment = wingConfig?.segments?.[selectedXsecIndex ?? 0];
  const initialRoot = segment
    ? airfoilShortName(segment.root_airfoil?.airfoil ?? "naca0012")
    : "naca0012";
  const initialTip = segment
    ? airfoilShortName(segment.tip_airfoil?.airfoil ?? initialRoot)
    : initialRoot;

  const [rootAirfoil, setRootAirfoil] = useState(initialRoot);
  const [tipAirfoil, setTipAirfoil] = useState(initialTip);
  const [re, setRe] = useState(200000);
  const [ma, setMa] = useState(0.0);

  // Sync from wing config when it loads
  useEffect(() => {
    if (segment) {
      setRootAirfoil(
        airfoilShortName(segment.root_airfoil?.airfoil ?? "naca0012"),
      );
      setTipAirfoil(
        airfoilShortName(
          segment.tip_airfoil?.airfoil ??
            segment.root_airfoil?.airfoil ??
            "naca0012",
        ),
      );
    }
  }, [segment]);

  // The displayed airfoil is root_airfoil (primary selection)
  const { geometry, isLoading: geoLoading } = useAirfoilGeometry(rootAirfoil);
  const analysis = useAirfoilAnalysis();

  const segmentLabel = `segment ${selectedXsecIndex ?? 0}`;

  return (
    <div className="flex flex-1 gap-4 overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <AirfoilPreviewViewerPanel
          airfoilName={rootAirfoil}
          geometry={geometry}
          geometryLoading={geoLoading}
          analysisResult={analysis.result}
          re={re}
          ma={ma}
          onReChange={setRe}
          onMaChange={setMa}
        />
      </div>
      <div className="shrink-0 overflow-hidden" style={{ width: 480 }}>
        <AirfoilPreviewConfigPanel
          rootAirfoil={rootAirfoil}
          tipAirfoil={tipAirfoil}
          onRootAirfoilChange={(name) => {
            setRootAirfoil(name);
            analysis.clear();
          }}
          onTipAirfoilChange={setTipAirfoil}
          onRunAnalysis={() => analysis.run(rootAirfoil, re, ma)}
          onClearResults={analysis.clear}
          isRunning={analysis.isRunning}
          segmentLabel={segmentLabel}
          segmentProps={{
            length: segment?.length,
            sweep: segment?.sweep,
            dihedral:
              segment?.root_airfoil?.dihedral_as_rotation_in_degrees,
            incidence: segment?.root_airfoil?.incidence,
          }}
        />
      </div>
    </div>
  );
}
