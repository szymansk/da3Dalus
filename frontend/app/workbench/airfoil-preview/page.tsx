"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWingConfig } from "@/hooks/useWingConfig";
import { useAirfoilGeometry } from "@/hooks/useAirfoilGeometry";
import { useAirfoilAnalysis } from "@/hooks/useAirfoilAnalysis";
import { useAirfoilSuitability } from "@/hooks/useAirfoilSuitability";
import { AirfoilPreviewViewerPanel } from "@/components/workbench/AirfoilPreviewViewerPanel";
import type { OperatingPoints } from "@/components/workbench/AirfoilPreviewViewerPanel";
import { AirfoilPreviewConfigPanel } from "@/components/workbench/AirfoilPreviewConfigPanel";

export function airfoilShortName(raw: string): string {
  return (raw.split("/").pop() ?? raw).replace(/\.dat$/i, "");
}

/**
 * Returns the score to display in the dropdown badge for a suitability item,
 * based on the active lens from the backend query.
 *
 * Relationship:
 *  - 'mission'          → item.mission ?? item.re_agnostic (fallback when no mission score)
 *  - 'target_cl_cruise' → item.target_cl_cruise ?? item.re_agnostic
 *  - 're_agnostic' / default → item.re_agnostic
 *
 * Note: target_cl_best_glide and target_cl_min_sink are display-only — never ranking lenses.
 */
export function activeLensScore(
  item: { re_agnostic: number; mission: number | null; target_cl_cruise: number | null },
  lens: string | undefined,
): number {
  if (lens === "mission") return item.mission ?? item.re_agnostic;
  if (lens === "target_cl_cruise") return item.target_cl_cruise ?? item.re_agnostic;
  return item.re_agnostic;
}

const NU_AIR = 1.46e-5; // kinematic viscosity [m\u00B2/s] at 15\u00B0C

export function computeRe(velocityMs: number, chordMm: number): number {
  return Math.round((velocityMs * (chordMm / 1000)) / NU_AIR);
}

/**
 * gh-825: Returns [name] as the include param for useAirfoilSuitability, or
 * undefined when the name is empty / is the placeholder '\u2014'.
 * Extracted as a module-level helper to keep AirfoilPreviewPage within
 * sonarjs/cognitive-complexity budget.
 */
export function toInclude(name: string): string[] | undefined {
  return name && name !== "\u2014" ? [name] : undefined;
}

export default function AirfoilPreviewPage() {
  const router = useRouter();
  const { aeroplaneId, selectedWing, selectedXsecIndex, selectXsec } =
    useAeroplaneContext();
  const { wingConfig, saveWingConfig } = useWingConfig(aeroplaneId, selectedWing);
  const [isSaving, setIsSaving] = useState(false);

  const segment = wingConfig?.segments?.[selectedXsecIndex ?? 0];
  const initialRoot = segment
    ? airfoilShortName(segment.root_airfoil?.airfoil ?? "naca0015")
    : "naca0015";
  const initialTip = segment
    ? airfoilShortName(segment.tip_airfoil?.airfoil ?? initialRoot)
    : initialRoot;

  const [rootAirfoil, setRootAirfoil] = useState(initialRoot);
  const [tipAirfoil, setTipAirfoil] = useState(initialTip);
  const [velocity, setVelocity] = useState(14); // m/s — typical model aircraft cruise
  const [ma, setMa] = useState(0);

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
  const tipGeo = useAirfoilGeometry(tipAirfoil === rootAirfoil ? null : tipAirfoil);
  const rootAnalysis = useAirfoilAnalysis();
  const tipAnalysis = useAirfoilAnalysis();

  // gh-822: Suitability hooks (chord in metres = chordMm / 1000)
  const [rootRankedMode, setRootRankedMode] = useState(false);
  const [tipRankedMode, setTipRankedMode] = useState(false);

  const rootSuitability = useAirfoilSuitability({
    chord_m: rootChordMm / 1000,
    speed_ms: velocity,
    aeroplane_id: aeroplaneId,
    // gh-825 ADDITIVE: always score the selected airfoil even if outside top-N
    include: toInclude(rootAirfoil),
  });
  const tipSuitability = useAirfoilSuitability({
    chord_m: tipChordMm / 1000,
    speed_ms: velocity,
    aeroplane_id: aeroplaneId,
    include: toInclude(tipAirfoil),
  });

  // Build lookup maps: airfoil name -> score string + sorted names.
  // The displayed score uses the active lens so the badge matches the ranking order.
  const rootScoreMap = useMemo((): Record<string, string> => {
    if (!rootSuitability.data) return {};
    const lens = rootSuitability.data.query.active_lens;
    return Object.fromEntries(
      rootSuitability.data.results.map((item) => [
        item.airfoil_name,
        activeLensScore(item, lens).toFixed(2),
      ]),
    );
  }, [rootSuitability.data]);

  const tipScoreMap = useMemo((): Record<string, string> => {
    if (!tipSuitability.data) return {};
    const lens = tipSuitability.data.query.active_lens;
    return Object.fromEntries(
      tipSuitability.data.results.map((item) => [
        item.airfoil_name,
        activeLensScore(item, lens).toFixed(2),
      ]),
    );
  }, [tipSuitability.data]);

  const rootSortedNames = useMemo(
    () => rootSuitability.data?.results.map((item) => item.airfoil_name),
    [rootSuitability.data],
  );

  const tipSortedNames = useMemo(
    () => tipSuitability.data?.results.map((item) => item.airfoil_name),
    [tipSuitability.data],
  );

  // Find the selected airfoil's suitability item
  const rootSuitabilityItem = useMemo(
    () => rootSuitability.data?.results.find((item) => item.airfoil_name === rootAirfoil) ?? null,
    [rootSuitability.data, rootAirfoil],
  );

  const tipSuitabilityItem = useMemo(
    () => tipSuitability.data?.results.find((item) => item.airfoil_name === tipAirfoil) ?? null,
    [tipSuitability.data, tipAirfoil],
  );

  // gh-822: Compute operating alpha from operating CL via the L/D polar
  // (find closest CL index in the analysis result)
  const rootOperatingAlpha = useMemo((): number | undefined => {
    if (!rootAnalysis.result) return undefined;
    const targetCl = rootSuitabilityItem?.target_cl_cruise;
    if (targetCl == null) return undefined;
    const cls = rootAnalysis.result.cl;
    let closestIdx = 0;
    let closestDist = Math.abs((cls[0] ?? 0) - targetCl);
    for (let i = 1; i < cls.length; i++) {
      const v = cls[i];
      if (v == null) continue;
      const d = Math.abs(v - targetCl);
      if (d < closestDist) {
        closestDist = d;
        closestIdx = i;
      }
    }
    return rootAnalysis.result.alphaDeg[closestIdx];
  }, [rootAnalysis.result, rootSuitabilityItem]);

  // gh-839: Compute operating points (alpha positions) for the three design-speed lenses.
  // Each target CL is mapped to an alpha via the analysis CL-alpha curve.
  function clToAlpha(targetCl: number | null | undefined): number | undefined {
    if (targetCl == null || !rootAnalysis.result) return undefined;
    const cls = rootAnalysis.result.cl;
    const alphas = rootAnalysis.result.alphaDeg;
    if (cls.length === 0) return undefined;
    let closestIdx = 0;
    let closestDist = Math.abs((cls[0] ?? 0) - targetCl);
    for (let i = 1; i < cls.length; i++) {
      const v = cls[i];
      if (v == null) continue;
      const d = Math.abs(v - targetCl);
      if (d < closestDist) {
        closestDist = d;
        closestIdx = i;
      }
    }
    return alphas[closestIdx];
  }

  const rootOperatingPoints = useMemo((): OperatingPoints | undefined => {
    if (!rootAnalysis.result || !rootSuitabilityItem) return undefined;
    const q = rootSuitability.data?.query;
    const alphaCruise = clToAlpha(rootSuitabilityItem.target_cl_cruise);
    const alphaBestGlide = clToAlpha(rootSuitabilityItem.target_cl_best_glide);
    const alphaMinSink = clToAlpha(rootSuitabilityItem.target_cl_min_sink);

    const pts: OperatingPoints = {};
    if (alphaCruise != null && q?.v_cruise_mps != null) {
      pts.cruise = { alpha: alphaCruise, label: `Cruise ${q.v_cruise_mps.toFixed(1)} m/s` };
    }
    if (alphaBestGlide != null && q?.v_md_mps != null) {
      pts.bestGlide = { alpha: alphaBestGlide, label: `Best-Glide ${q.v_md_mps.toFixed(1)} m/s` };
    }
    if (alphaMinSink != null && q?.v_min_sink_mps != null) {
      pts.minSink = { alpha: alphaMinSink, label: `Min-Sink ${q.v_min_sink_mps.toFixed(1)} m/s` };
    }
    if (!pts.cruise && !pts.bestGlide && !pts.minSink) return undefined;
    return pts;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rootAnalysis.result, rootSuitabilityItem, rootSuitability.data?.query]);

  // Sync airfoils from segment when index or wingConfig changes
  useEffect(() => {
    const seg = wingConfig?.segments?.[selectedXsecIndex ?? 0];
    if (!seg) return;
    setRootAirfoil(
      airfoilShortName(seg.root_airfoil?.airfoil ?? "naca0015"),
    );
    setTipAirfoil(
      airfoilShortName(
        seg.tip_airfoil?.airfoil ??
          seg.root_airfoil?.airfoil ??
          "naca0015",
      ),
    );
    setRootReOverride(null);
    setTipReOverride(null);
    // Analysis will auto-run via the effect below
  }, [selectedXsecIndex, wingConfig]);

  const hasTip = tipAirfoil !== rootAirfoil;

  // Auto-run analysis whenever airfoil, Re, or Ma changes
  useEffect(() => {
    if (!rootAirfoil) return;
    rootAnalysis.run(rootAirfoil, rootRe, ma);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rootAirfoil, rootRe, ma]);

  useEffect(() => {
    if (!hasTip || !tipAirfoil) { tipAnalysis.clear(); return; }
    tipAnalysis.run(tipAirfoil, tipRe, ma);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipAirfoil, tipRe, ma, hasTip]);

  // Detect if airfoils changed vs. saved state
  const savedRoot = segment ? airfoilShortName(segment.root_airfoil?.airfoil ?? "naca0015") : "naca0015";
  const savedTip = segment ? airfoilShortName(segment.tip_airfoil?.airfoil ?? segment.root_airfoil?.airfoil ?? "naca0015") : "naca0015";
  const isDirty = rootAirfoil !== savedRoot || tipAirfoil !== savedTip;

  const handleRevert = useCallback(() => {
    setRootAirfoil(savedRoot);
    setTipAirfoil(savedTip);
    setRootReOverride(null);
    setTipReOverride(null);
    // Analysis auto-re-runs via effects
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
          operatingAlphaDeg={rootOperatingAlpha}
          tipSuitabilityItem={hasTip ? (tipSuitabilityItem ?? undefined) : undefined}
          operatingPoints={rootOperatingPoints}
        />
      </div>
      <div className="shrink-0 overflow-hidden" style={{ width: 480 }}>
        <AirfoilPreviewConfigPanel
          rootAirfoil={rootAirfoil}
          tipAirfoil={tipAirfoil}
          onRootAirfoilChange={setRootAirfoil}
          onTipAirfoilChange={setTipAirfoil}
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
          rootSuitabilityItem={rootSuitabilityItem ?? undefined}
          rootSuitabilityNotFound={
            !rootSuitability.isLoading &&
            rootSuitability.data != null &&
            rootSuitabilityItem == null
          }
          tipSuitabilityItem={hasTip ? (tipSuitabilityItem ?? undefined) : undefined}
          tipSuitabilityNotFound={
            hasTip &&
            !tipSuitability.isLoading &&
            tipSuitability.data != null &&
            tipSuitabilityItem == null
          }
          rootScoreMap={rootRankedMode ? rootScoreMap : undefined}
          tipScoreMap={tipRankedMode ? tipScoreMap : undefined}
          rootSortedNames={rootRankedMode ? rootSortedNames : undefined}
          tipSortedNames={tipRankedMode ? tipSortedNames : undefined}
          rootRankedMode={rootRankedMode}
          onRootRankedModeToggle={() => setRootRankedMode((v) => !v)}
          tipRankedMode={tipRankedMode}
          onTipRankedModeToggle={() => setTipRankedMode((v) => !v)}
          targetClProvenance={rootSuitability.data?.query.target_cl_provenance}
          suitabilityCaveat={rootSuitability.data?.caveat}
          suitabilitySpeedContext={
            rootSuitability.data?.query
              ? {
                  v_cruise_mps: rootSuitability.data.query.v_cruise_mps,
                  v_md_mps: rootSuitability.data.query.v_md_mps,
                  v_min_sink_mps: rootSuitability.data.query.v_min_sink_mps,
                }
              : undefined
          }
        />
      </div>
    </div>
  );
}
