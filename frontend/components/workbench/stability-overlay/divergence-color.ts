/**
 * Color class for CG divergence indicator (SOLL vs IST).
 *
 * Returns a Tailwind text-color class based on the absolute delta
 * between design CG (`cgSoll`) and aggregated CG (`cgIst`), normalised
 * by MAC.
 */
export function cgDivergenceColor(
  cgSoll: number,
  cgIst: number,
  mac: number,
): string {
  const deltaPct = (Math.abs(cgIst - cgSoll) / mac) * 100;
  // Thresholds (match the original InfoChipRow behaviour):
  //   deltaPct < 5      → emerald-400 (in tolerance)
  //   5 ≤ deltaPct ≤ 15 → orange-400  (drift / caution)
  //   deltaPct > 15     → red-400     (out of envelope)
  if (deltaPct < 5) return "text-emerald-400";
  if (deltaPct <= 15) return "text-orange-400";
  return "text-red-400";
}
