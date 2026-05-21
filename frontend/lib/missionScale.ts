import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";
import type { MissionKpiSet } from "@/hooks/useMissionKpis";

export const AXES: AxisName[] = [
  "stall_safety",
  "glide",
  "climb",
  "cruise",
  "maneuver",
  "wing_loading",
  "field_friendliness",
];

export type AxisRange = [number, number];
export type AxisRanges = Record<AxisName, AxisRange>;

/** Union the per-axis range across all supplied missions. */
function unionMissionRanges(activeMissions: MissionPreset[]): AxisRanges {
  const out = {} as AxisRanges;
  for (const axis of AXES) {
    let lo = Infinity;
    let hi = -Infinity;
    for (const m of activeMissions) {
      const [a, b] = m.axis_ranges[axis];
      if (a < lo) lo = a;
      if (b > hi) hi = b;
    }
    out[axis] = [lo, hi];
  }
  return out;
}

/** Widen `out` so it covers the Ist KPI's reference range + actual value. */
function widenWithIst(out: AxisRanges, ist: MissionKpiSet): void {
  for (const axis of AXES) {
    const k = ist.ist_polygon[axis];
    if (!k || k.provenance === "missing") continue;
    const score = k.score_0_1 ?? 0;
    const istValue = k.range_min + score * (k.range_max - k.range_min);
    const lo = Math.min(out[axis][0], k.range_min, istValue);
    const hi = Math.max(out[axis][1], k.range_max, istValue);
    out[axis] = [lo, hi];
  }
}

/**
 * Combine multiple mission presets' per-axis ranges (and, optionally, the
 * Ist KPI's own ranges + values) into one set.
 *
 * Without `ist`: result for each axis = [min(all mins), max(all maxes)] across
 * the supplied missions.
 *
 * With `ist` (gh-601): the union also includes the KPI's reference range
 * AND the actual raw Ist value. This keeps the orange Ist polygon visible
 * even when the active mission's `axis_ranges` are narrower than the
 * aircraft's actual KPIs (e.g. a Wing-Racer preset with cruise range
 * `[25, 40]` should not collapse the cruise vertex of an aircraft that
 * actually cruises at 18 m/s). Axes whose Ist provenance is "missing" are
 * skipped to avoid polluting the range with stale zeros.
 */
export function computeAxisRanges(
  activeMissions: MissionPreset[],
  ist?: MissionKpiSet,
): AxisRanges {
  if (activeMissions.length === 0) {
    return Object.fromEntries(AXES.map((a) => [a, [0, 1]])) as AxisRanges;
  }
  const out = unionMissionRanges(activeMissions);
  if (ist) widenWithIst(out, ist);
  return out;
}

/**
 * Re-normalise a 0..1 score from a preset's *local* range to a *global*
 * range so it sits correctly on the auto-scaled chart.
 */
export function renormalise(
  score: number,
  localRange: AxisRange,
  globalRange: AxisRange,
): number {
  const localValue = localRange[0] + score * (localRange[1] - localRange[0]);
  const span = globalRange[1] - globalRange[0];
  if (span <= 0) return 0;
  return Math.max(0, Math.min(1, (localValue - globalRange[0]) / span));
}

/**
 * Linearly map a 0..1 normalised score onto its axis range to recover the
 * raw physical value: `range[0] + score × (range[1] − range[0])`.
 *
 * Clamps the score to [0, 1] to guard against out-of-band KPI readings.
 */
export function normalizedToRaw(score: number, range: AxisRange): number {
  const clamped = Math.max(0, Math.min(1, score));
  return range[0] + clamped * (range[1] - range[0]);
}

/** Display unit for each axis — used by the radar hover tooltip. */
export const AXIS_UNITS: Record<AxisName, string> = {
  stall_safety: "×",
  glide: "L/D",
  climb: "—",
  cruise: "m/s",
  maneuver: "g",
  wing_loading: "N/m²",
  field_friendliness: "—",
};

/** Convert a 0..1 score on a given axis-index (out of 7) into SVG (x, y). */
export function polarToCartesian(
  axisIndex: number,
  score: number,
  radius: number,
): { x: number; y: number } {
  const angle = (Math.PI * 2 * axisIndex) / 7 - Math.PI / 2;
  return {
    x: Math.cos(angle) * score * radius,
    y: Math.sin(angle) * score * radius,
  };
}
