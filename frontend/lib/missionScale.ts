import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";

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

/**
 * Combine multiple mission presets' per-axis ranges into one set.
 * For each axis, result = [min(all mins), max(all maxes)].
 */
export function computeAxisRanges(activeMissions: MissionPreset[]): AxisRanges {
  if (activeMissions.length === 0) {
    return Object.fromEntries(AXES.map((a) => [a, [0, 1]])) as AxisRanges;
  }
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
