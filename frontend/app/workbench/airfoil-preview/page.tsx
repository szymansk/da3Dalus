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

// Reynolds: Re = V * c / ν
const NU_AIR = 1.46e-5; // kinematic viscosity [m²/s] at 15°C
const V_CRUISE = 14; // typical model aircraft cruise speed [m/s]

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
  const [ma, setMa] = useState(0.0);

  const chordM = (segment?.root_airfoil?.chord ?? 200) / 1000;
  const defaultRe = Math.round((V_CRUISE * chordM) / NU_AIR);
  const [re, setRe] = useState(defaultRe);

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
      const c = (segment.root_airfoil?.chord ?? 200) / 1000;
      setRe(Math.round((V_CRUISE * c) / NU_AIR));
    }
  }, [segment]);

  // Geometry for both airfoils
  const rootGeo = useAirfoilGeometry(rootAirfoil);
  const tipGeo = useAirfoilGeometry(tipAirfoil !== rootAirfoil ? tipAirfoil : null);

  // Analysis for both airfoils (triggered by Run Analysis button)
  const rootAnalysis = useAirfoilAnalysis();
  const tipAnalysis = useAirfoilAnalysis();

  const handleRunAnalysis = () => {
    rootAnalysis.run(rootAirfoil, re, ma);
    if (tipAirfoil !== rootAirfoil) {
      tipAnalysis.run(tipAirfoil, re, ma);
    }
  };

  const handleClear = () => {
    rootAnalysis.clear();
    tipAnalysis.clear();
  };

  const segmentLabel = `segment ${selectedXsecIndex ?? 0}`;

  return (
    <div className="flex flex-1 gap-4 overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <AirfoilPreviewViewerPanel
          rootAirfoilName={rootAirfoil}
          tipAirfoilName={tipAirfoil !== rootAirfoil ? tipAirfoil : null}
          rootGeometry={rootGeo.geometry}
          tipGeometry={tipGeo.geometry}
          geometryLoading={rootGeo.isLoading || tipGeo.isLoading}
          rootAnalysisResult={rootAnalysis.result}
          tipAnalysisResult={tipAirfoil !== rootAirfoil ? tipAnalysis.result : null}
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
            rootAnalysis.clear();
          }}
          onTipAirfoilChange={(name) => {
            setTipAirfoil(name);
            tipAnalysis.clear();
          }}
          onRunAnalysis={handleRunAnalysis}
          onClearResults={handleClear}
          isRunning={rootAnalysis.isRunning || tipAnalysis.isRunning}
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
