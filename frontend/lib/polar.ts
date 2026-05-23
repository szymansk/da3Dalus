/**
 * Pure derivation helpers for the parabolic polar
 * `C_D = C_D0 + C_L²/(π·e·AR)` — Anderson §6.7.2.
 *
 * The ρ-bail rule (gh-626 spec §8.5): when the AeroBuildup parabolic
 * fit was rejected (`e_oswald_fallback_used = true`), the polar is
 * NOT parabolic. Computing parabolic-polar metrics on it produces
 * measurement-shaped non-measurements, so every derived helper here
 * bails to `null` in that case.
 */

export type EQuality = "high" | "medium" | "low" | "unknown";

export type RhoThresholds = { readonly amber: number; readonly red: number };

function valid(...vs: (number | null | undefined)[]): boolean {
  // Reject null / undefined / non-finite (NaN, ±Infinity) / non-positive.
  // Non-finite inputs are a corrupt-payload symptom — a backend bug like
  // `np.inf` from a degenerate fit would otherwise produce "Infinity" /
  // "0" chip values instead of the documented "—" bail state.
  return vs.every((v) => v != null && Number.isFinite(v) && v > 0);
}

/** k = 1/(π·e·AR). Returns null on fit rejection or invalid inputs. */
export function computeK(
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(eFromCtx, ar)) return null;
  return 1 / (Math.PI * (eFromCtx as number) * (ar as number));
}

/** C_L,md = √(π·e·AR·C_D0). Lift coefficient at maximum L/D. */
export function computeCLmd(
  cd0: number | null | undefined,
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(cd0, eFromCtx, ar)) return null;
  return Math.sqrt(
    Math.PI * (eFromCtx as number) * (ar as number) * (cd0 as number),
  );
}

/** (L/D)_max = ½·√(π·e·AR / C_D0). Canonical Scholz §5.7 polar-quality scalar. */
export function computeEMax(
  cd0: number | null | undefined,
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(cd0, eFromCtx, ar)) return null;
  return (
    0.5 *
    Math.sqrt((Math.PI * (eFromCtx as number) * (ar as number)) / (cd0 as number))
  );
}

/**
 * Degeneracy ratio ρ = C_D0·π·e·AR / C_L,max² = (C_L,md / C_L,max)².
 * Anderson §6.7.2 derivation: ρ=1 ⇔ V_md=V_stall, ρ=1/3 ⇔ V_min,sink=V_stall.
 */
export function computeRho(
  cd0: number | null | undefined,
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
  clMax: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(cd0, eFromCtx, ar, clMax)) return null;
  const e = eFromCtx as number;
  const c = clMax as number;
  return ((cd0 as number) * Math.PI * e * (ar as number)) / (c * c);
}

/** Profile-aware ρ traffic-light thresholds (Scholz §5.7 + spec rev 2 decision 9). */
export function rhoThresholdsForProfile(isGlider: boolean): RhoThresholds {
  return isGlider ? { amber: 2 / 3, red: 1.0 } : { amber: 1 / 3, red: 1.0 };
}

/** Maps the backend's e-fit quality label to a Tailwind value-colour class. */
export function qualityColorClassName(
  quality: EQuality | undefined | null,
): string {
  switch (quality) {
    case "high":
      return "text-emerald-400";
    case "medium":
      return "text-amber-400";
    case "low":
      return "text-orange-400";
    case "unknown":
    default:
      return "text-muted-foreground";
  }
}

/** ρ traffic-light colour. Lower-inclusive boundaries. */
export function rhoColorClassName(rho: number | null, isGlider: boolean): string {
  if (rho == null) return "text-muted-foreground";
  const { amber, red } = rhoThresholdsForProfile(isGlider);
  if (rho >= red) return "text-red-400";
  if (rho >= amber) return "text-amber-400";
  return "text-emerald-400";
}
