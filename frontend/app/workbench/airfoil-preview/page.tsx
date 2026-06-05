"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWingConfig } from "@/hooks/useWingConfig";
import { useAirfoilGeometry } from "@/hooks/useAirfoilGeometry";
import { useAirfoilAnalysis } from "@/hooks/useAirfoilAnalysis";
import { useAirfoilSuitability } from "@/hooks/useAirfoilSuitability";
import { useSpeedPolar } from "@/hooks/useSpeedPolar";
import { useSectionAoa, sectionForXsecIndex } from "@/hooks/useSectionAoa";
import { AirfoilPreviewViewerPanel } from "@/components/workbench/AirfoilPreviewViewerPanel";
import type { OperatingPoints } from "@/components/workbench/AirfoilPreviewViewerPanel";
import { AirfoilPreviewConfigPanel } from "@/components/workbench/AirfoilPreviewConfigPanel";
import { emptyFilters } from "@/components/workbench/AirfoilSuitabilityFilterBar";
import type { AirfoilSuitabilityFilters } from "@/components/workbench/AirfoilSuitabilityFilterBar";
import type { AirfoilFamily, RoleTag } from "@/hooks/useAirfoilSuitability";

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

/**
 * Derive the saved airfoil short-name for a segment slot, defaulting to 'naca0015'.
 * Extracted at module level to reduce cognitive complexity of AirfoilPreviewPage.
 */
export function savedSlotName(
  segment: { root_airfoil?: { airfoil?: string } | null; tip_airfoil?: { airfoil?: string } | null } | undefined,
  slot: "root" | "tip",
): string {
  if (!segment) return "naca0015";
  if (slot === "root") return airfoilShortName(segment.root_airfoil?.airfoil ?? "naca0015");
  return airfoilShortName(
    segment.tip_airfoil?.airfoil ?? segment.root_airfoil?.airfoil ?? "naca0015",
  );
}

/**
 * Collect unique airfoil names used in all segments of a wing config.
 * Extracted at module level to reduce cognitive complexity of AirfoilPreviewPage.
 */
export function collectUsedAirfoilNames(
  segments: Array<{
    root_airfoil?: { airfoil?: string } | null;
    tip_airfoil?: { airfoil?: string } | null;
  }>,
): string[] {
  const names: string[] = [];
  for (const seg of segments) {
    if (seg.root_airfoil?.airfoil) names.push(airfoilShortName(seg.root_airfoil.airfoil));
    if (seg.tip_airfoil?.airfoil) names.push(airfoilShortName(seg.tip_airfoil.airfoil));
  }
  return Array.from(new Set(names));
}

/**
 * gh-835: Convert AirfoilSuitabilityFilters to query-param shape for useAirfoilSuitability.
 * Extracted at module level to reduce cognitive complexity of AirfoilPreviewPage.
 * Undefined return values mean "no filter" (additive; old callers unaffected).
 */
export function toSuitabilityQueryFilters(filters: AirfoilSuitabilityFilters): {
  family: AirfoilFamily[] | undefined;
  tags: RoleTag[] | undefined;
  thickness_min_pct: number | undefined;
  thickness_max_pct: number | undefined;
} {
  return {
    family: filters.families.length > 0 ? filters.families : undefined,
    tags: filters.tags.length > 0 ? filters.tags : undefined,
    thickness_min_pct:
      filters.thicknessMinPct !== "" ? Number(filters.thicknessMinPct) : undefined,
    thickness_max_pct:
      filters.thicknessMaxPct !== "" ? Number(filters.thicknessMaxPct) : undefined,
  };
}

/**
 * Map a target CL to the closest alpha in an analysis result CL-alpha curve.
 * Extracted at module level to reduce cognitive complexity of AirfoilPreviewPage.
 */
export function clToAlpha(
  targetCl: number | null | undefined,
  cls: (number | null)[],
  alphas: number[],
): number | undefined {
  if (targetCl == null || cls.length === 0) return undefined;
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

/**
 * Build an OperatingPoints map from a suitability item + analysis result.
 * Extracted at module level to reduce cognitive complexity of AirfoilPreviewPage.
 */
export function buildOperatingPoints(
  suitabilityItem: { target_cl_cruise: number | null; target_cl_best_glide: number | null; target_cl_min_sink: number | null },
  cls: (number | null)[],
  alphas: number[],
  query: { v_cruise_mps: number | null; v_md_mps: number | null; v_min_sink_mps: number | null } | undefined,
): OperatingPoints | undefined {
  const alphaCruise = clToAlpha(suitabilityItem.target_cl_cruise, cls, alphas);
  const alphaBestGlide = clToAlpha(suitabilityItem.target_cl_best_glide, cls, alphas);
  const alphaMinSink = clToAlpha(suitabilityItem.target_cl_min_sink, cls, alphas);

  const pts: OperatingPoints = {};
  if (alphaCruise != null && query?.v_cruise_mps != null) {
    pts.cruise = { alpha: alphaCruise, label: `Cruise ${query.v_cruise_mps.toFixed(1)} m/s` };
  }
  if (alphaBestGlide != null && query?.v_md_mps != null) {
    pts.bestGlide = { alpha: alphaBestGlide, label: `Best-Glide ${query.v_md_mps.toFixed(1)} m/s` };
  }
  if (alphaMinSink != null && query?.v_min_sink_mps != null) {
    pts.minSink = { alpha: alphaMinSink, label: `Min-Sink ${query.v_min_sink_mps.toFixed(1)} m/s` };
  }
  return (pts.cruise ?? pts.bestGlide ?? pts.minSink) ? pts : undefined;
}

export default function AirfoilPreviewPage() {
  const router = useRouter();
  const { aeroplaneId, selectedWing, selectedXsecIndex, selectXsec } =
    useAeroplaneContext();
  const { wingConfig, saveWingConfig } = useWingConfig(aeroplaneId, selectedWing);
  const [isSaving, setIsSaving] = useState(false);

  const segment = wingConfig?.segments?.[selectedXsecIndex ?? 0];
  const initialRoot = savedSlotName(segment, "root");
  const initialTip = savedSlotName(segment, "tip");

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

  // gh-841: aircraft speed polar from the backend (closed-form from assumptions)
  const speedPolar = useSpeedPolar(aeroplaneId);

  // gh-840: per-section world AoA via LiftingLine (as-built operating condition)
  const sectionAoa = useSectionAoa(aeroplaneId, selectedWing);

  // gh-822: Suitability hooks (chord in metres = chordMm / 1000)
  const [rootRankedMode, setRootRankedMode] = useState(false);
  const [tipRankedMode, setTipRankedMode] = useState(false);

  // gh-835: shared filter state (applied to both root + tip suitability queries)
  const [suitabilityFilters, setSuitabilityFilters] = useState<AirfoilSuitabilityFilters>(
    () => emptyFilters(),
  );

  // gh-835: convert filter state to query params
  const filterQueryParams = toSuitabilityQueryFilters(suitabilityFilters);

  const rootSuitability = useAirfoilSuitability({
    chord_m: rootChordMm / 1000,
    speed_ms: velocity,
    aeroplane_id: aeroplaneId,
    // gh-825 ADDITIVE: always score the selected airfoil even if outside top-N
    include: toInclude(rootAirfoil),
    // gh-835 ADDITIVE: filter params
    ...filterQueryParams,
  });
  const tipSuitability = useAirfoilSuitability({
    chord_m: tipChordMm / 1000,
    speed_ms: velocity,
    aeroplane_id: aeroplaneId,
    include: toInclude(tipAirfoil),
    // gh-835 ADDITIVE: same filter params for tip
    ...filterQueryParams,
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

  // gh-837: collect all airfoil names used across the current aeroplane model
  const usedAirfoilNames = useMemo(
    () => (wingConfig?.segments ? collectUsedAirfoilNames(wingConfig.segments) : []),
    [wingConfig],
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

  // gh-840: Derive the as-built effective AoA for the currently selected section.
  // Uses the section closest to the selected xsec index within the LiftingLine span data.
  const segmentCount = wingConfig?.segments?.length ?? 1;
  const asBuiltAlphaDeg = useMemo((): number | null => {
    if (!sectionAoa.data || sectionAoa.data.sections.length === 0) return null;
    const section = sectionForXsecIndex(
      sectionAoa.data.sections,
      selectedXsecIndex ?? 0,
      segmentCount,
    );
    return section?.alpha_effective_deg ?? null;
  }, [sectionAoa.data, selectedXsecIndex, segmentCount]);

  // gh-822: Compute operating alpha from operating CL via the L/D polar
  // (find closest CL index in the analysis result)
  const rootOperatingAlpha = useMemo((): number | undefined => {
    if (!rootAnalysis.result) return undefined;
    return clToAlpha(
      rootSuitabilityItem?.target_cl_cruise ?? null,
      rootAnalysis.result.cl,
      rootAnalysis.result.alphaDeg,
    );
  }, [rootAnalysis.result, rootSuitabilityItem]);

  // gh-839: Compute operating points (alpha positions) for the three design-speed lenses.
  const rootOperatingPoints = useMemo((): OperatingPoints | undefined => {
    if (!rootAnalysis.result || !rootSuitabilityItem) return undefined;
    return buildOperatingPoints(
      rootSuitabilityItem,
      rootAnalysis.result.cl,
      rootAnalysis.result.alphaDeg,
      rootSuitability.data?.query,
    );
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
  const savedRoot = savedSlotName(segment, "root");
  const savedTip = savedSlotName(segment, "tip");
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
          // gh-841: speed polar + 2D proxy charts
          speedPolar={speedPolar.data ?? null}
          speedPolarLoading={speedPolar.isLoading}
          // gh-840: as-built world AoA from LiftingLine (null when no aero/op-point)
          asBuiltAlphaDeg={asBuiltAlphaDeg}
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
          usedAirfoilNames={usedAirfoilNames}
          // gh-835 ADDITIVE: filter bar (shown only when at least one ranked mode is active)
          suitabilityFilters={
            rootRankedMode || tipRankedMode ? suitabilityFilters : undefined
          }
          onSuitabilityFiltersChange={
            rootRankedMode || tipRankedMode ? setSuitabilityFilters : undefined
          }
        />
      </div>
    </div>
  );
}
