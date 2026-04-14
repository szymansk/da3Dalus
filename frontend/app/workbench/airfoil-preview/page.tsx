"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
  const { aeroplaneId, selectedWing, selectedXsecIndex, selectXsec } =
    useAeroplaneContext();
  const { wingConfig, saveWingConfig } = useWingConfig(aeroplaneId, selectedWing);
  const [isSaving, setIsSaving] = useState(false);

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

  const rootGeo = useAirfoilGeometry(rootAirfoil);
  const tipGeo = useAirfoilGeometry(tipAirfoil !== rootAirfoil ? tipAirfoil : null);
  const rootAnalysis = useAirfoilAnalysis();
  const tipAnalysis = useAirfoilAnalysis();

  // Sync airfoils from segment when index or wingConfig changes
  useEffect(() => {
    const seg = wingConfig?.segments?.[selectedXsecIndex ?? 0];
    if (!seg) return;
    setRootAirfoil(
      airfoilShortName(seg.root_airfoil?.airfoil ?? "naca0012"),
    );
    setTipAirfoil(
      airfoilShortName(
        seg.tip_airfoil?.airfoil ??
          seg.root_airfoil?.airfoil ??
          "naca0012",
      ),
    );
    setRootReOverride(null);
    setTipReOverride(null);
    rootAnalysis.clear();
    tipAnalysis.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedXsecIndex, wingConfig]);

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

  // Detect if airfoils changed vs. saved state
  const savedRoot = segment ? airfoilShortName(segment.root_airfoil?.airfoil ?? "naca0012") : "naca0012";
  const savedTip = segment ? airfoilShortName(segment.tip_airfoil?.airfoil ?? segment.root_airfoil?.airfoil ?? "naca0012") : "naca0012";
  const isDirty = rootAirfoil !== savedRoot || tipAirfoil !== savedTip;

  const handleRevert = useCallback(() => {
    setRootAirfoil(savedRoot);
    setTipAirfoil(savedTip);
    setRootReOverride(null);
    setTipReOverride(null);
    rootAnalysis.clear();
    tipAnalysis.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedRoot, savedTip]);

  const handleSave = useCallback(async () => {
    if (!wingConfig || !segment) return;
    setIsSaving(true);
    try {
      const idx = selectedXsecIndex ?? 0;
      const updatedSegments = wingConfig.segments.map((seg, i) => {
        if (i !== idx) return seg;
        return {
          ...seg,
          root_airfoil: { ...seg.root_airfoil, airfoil: rootAirfoil },
          tip_airfoil: { ...seg.tip_airfoil, airfoil: tipAirfoil },
        };
      });
      await saveWingConfig({ ...wingConfig, segments: updatedSegments });
    } finally {
      setIsSaving(false);
    }
  }, [wingConfig, segment, selectedXsecIndex, rootAirfoil, tipAirfoil, saveWingConfig]);

  const handleBack = () => {
    router.push("/workbench");
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
          segmentIndex={selectedXsecIndex ?? 0}
          segmentCount={wingConfig?.segments?.length ?? 1}
          onSegmentChange={selectXsec}
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
          isDirty={isDirty}
          isSaving={isSaving}
          onSave={handleSave}
          onRevert={handleRevert}
          onBack={handleBack}
        />
      </div>
    </div>
  );
}
