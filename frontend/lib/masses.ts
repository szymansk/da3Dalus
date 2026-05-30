/**
 * Helpers for the German-formatted mass list used by the speed polar
 * (Geschwindigkeitspolare). Decimal separator is a comma, list separator a
 * semicolon, e.g. "1,5; 2,0; 2,5". A "." decimal separator is also accepted.
 *
 * Kept dependency-free so it can be unit-tested without loading the analysis
 * client-component graph.
 */

/** Parse a mass list. Empty, non-numeric and non-positive tokens are dropped. */
export function parseMasses(input: string): number[] {
  return input
    .split(";")
    .map((tok) => Number.parseFloat(tok.trim().replace(/,/g, ".")))
    .filter((n) => Number.isFinite(n) && n > 0);
}

/** Format a mass for the German-style input ("1.5" -> "1,5"). */
export function formatMass(m: number): string {
  return String(m).replace(".", ",");
}
