/**
 * Color class for CG divergence indicator (SOLL vs IST).
 *
 * Returns a Tailwind text-color class based on the absolute delta
 * between design CG (`cgSoll`) and aggregated CG (`cgIst`), normalised
 * by MAC.
 *
 * Thresholds and class names match the original InfoChipRow helper:
 *   |Δ|/MAC * 100 <  5%        → text-emerald-400 (in tolerance)
 *   5% <= |Δ|/MAC * 100 <= 15% → text-orange-400 (drift / caution)
 *   |Δ|/MAC * 100 >  15%       → text-red-400 (out of envelope)
 */
export function cgDivergenceColor(
  cgSoll: number,
  cgIst: number,
  mac: number,
): string {
  const deltaPct = (Math.abs(cgIst - cgSoll) / mac) * 100;
  if (deltaPct < 5) return "text-emerald-400";
  if (deltaPct <= 15) return "text-orange-400";
  return "text-red-400";
}
