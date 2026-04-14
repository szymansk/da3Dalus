"use client";

import { useState, useEffect, useMemo } from "react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWingConfig } from "@/hooks/useWingConfig";
import { useAirfoilGeometry } from "@/hooks/useAirfoilGeometry";
import { useAirfoilAnalysis } from "@/hooks/useAirfoilAnalysis";
import { AirfoilPreviewViewerPanel } from "@/components/workbench/AirfoilPreviewViewerPanel";
import { AirfoilPreviewConfigPanel } from "@/components/workbench/AirfoilPreviewConfigPanel";

function airfoilShortName(raw: string): string {
  return (raw.split("/").pop() ?? raw).replace(/\.dat$/i, "");
}

const NU_AIR = 1.46e-5; // kinematic viscosity [m\u00B2/s] at 15\u00B0C

export function computeRe(velocityMs: number, chordMm: number): number {
  return Math.round((velocityMs * (chordMm / 1000)) / NU_AIR);
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
  const [velocity, setVelocity] = useState(14); // m/s — typical model aircraft cruise
  const [ma, setMa] = useState(0.0);

  // Re computed reactively from velocity + chord
  const rootChordMm = segment?.root_airfoil?.chord ?? 200;
  const tipChordMm = segment?.tip_airfoil?.chord ?? rootChordMm;
  const [rootReOverride, setRootReOverride] = useState<number | null>(null);
  const [tipReOverride, setTipReOverride] = useState<number | null>(null);

  const rootRe = rootReOverride ?? computeRe(velocity, rootChordMm);
  const tipRe = tipReOverride ?? computeRe(velocity, tipChordMm);

  // Reset overrides when velocity changes (recalculate from velocity)
  useEffect(() => {
    setRootReOverride(null);
    setTipReOverride(null);
  }, [velocity]);

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
      setRootReOverride(null);
      setTipReOverride(null);
    }
  }, [segment]);

  const rootGeo = useAirfoilGeometry(rootAirfoil);
  const tipGeo = useAirfoilGeometry(tipAirfoil !== rootAirfoil ? tipAirfoil : null);
  const rootAnalysis = useAirfoilAnalysis();
  const tipAnalysis = useAirfoilAnalysis();

  const hasTip = tipAirfoil !== rootAirfoil;

  const handleRunAnalysis = () => {
    rootAnalysis.run(rootAirfoil, rootRe, ma);
    if (hasTip) {
      tipAnalysis.run(tipAirfoil, tipRe, ma);
    }
  };

  const handleClear = () => {
    rootAnalysis.clear();
    tipAnalysis.clear();
  };

  return (
    <div className="flex flex-1 gap-4 overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <AirfoilPreviewViewerPanel
          rootAirfoilName={rootAirfoil}
          tipAirfoilName={hasTip ? tipAirfoil : null}
          rootGeometry={rootGeo.geometry}
          tipGeometry={tipGeo.geometry}
          geometryLoading={rootGeo.isLoading || tipGeo.isLoading}
          rootAnalysisResult={rootAnalysis.result}
          tipAnalysisResult={hasTip ? tipAnalysis.result : null}
          rootRe={rootRe}
          tipRe={hasTip ? tipRe : null}
          ma={ma}
          onMaChange={setMa}
        />
      </div>
      <div className="shrink-0 overflow-hidden" style={{ width: 480 }}>
        <AirfoilPreviewConfigPanel
          rootAirfoil={rootAirfoil}
          tipAirfoil={tipAirfoil}
          onRootAirfoilChange={(name) => { setRootAirfoil(name); rootAnalysis.clear(); }}
          onTipAirfoilChange={(name) => { setTipAirfoil(name); tipAnalysis.clear(); }}
          onRunAnalysis={handleRunAnalysis}
          onClearResults={handleClear}
          isRunning={rootAnalysis.isRunning || tipAnalysis.isRunning}
          segmentLabel={`segment ${selectedXsecIndex ?? 0}`}
          segmentProps={{
            length: segment?.length,
            sweep: segment?.sweep,
            dihedral: segment?.root_airfoil?.dihedral_as_rotation_in_degrees,
            incidence: segment?.root_airfoil?.incidence,
          }}
          velocity={velocity}
          onVelocityChange={setVelocity}
          rootRe={rootRe}
          tipRe={tipRe}
          onRootReChange={setRootReOverride}
          onTipReChange={setTipReOverride}
          rootChordMm={rootChordMm}
          tipChordMm={tipChordMm}
        />
      </div>
    </div>
  );
}
