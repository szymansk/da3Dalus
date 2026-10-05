/**
 * Super-ellipse fuselage sections (gh-1157).
 *
 * Upper half (z >= 0): |y/a|^n + |z/b|^n = 1.
 * Lower half (z < 0):  same with `n_lower`, falling back to `n` when unset.
 * `a` and `b` are half-axes in metres.
 */
export interface SuperEllipseSection {
  a: number;
  b: number;
  n: number;
  n_lower?: number | null;
}

/** Exponent that governs the outline at polar parameter `theta`. */
export function sectionExponent(xs: SuperEllipseSection, theta: number): number {
  return Math.sin(theta) < 0 && xs.n_lower != null ? xs.n_lower : xs.n;
}

/** Lateral/vertical offset of the outline point at `theta` from the section centre. */
export function sectionOffset(
  xs: SuperEllipseSection,
  theta: number,
): { y: number; z: number } {
  const cosT = Math.cos(theta);
  const sinT = Math.sin(theta);
  const n = sectionExponent(xs, theta);
  return {
    y: xs.a * Math.sign(cosT) * Math.pow(Math.abs(cosT), 2 / n),
    z: xs.b * Math.sign(sinT) * Math.pow(Math.abs(sinT), 2 / n),
  };
}

/** Short label of the exponent(s), e.g. "n=2.0" or "n=2.0/8.0" (top/bottom). */
export function sectionExponentLabel(xs: SuperEllipseSection): string {
  if (xs.n_lower == null || xs.n_lower === xs.n) return `n=${xs.n.toFixed(1)}`;
  return `n=${xs.n.toFixed(1)}/${xs.n_lower.toFixed(1)}`;
}

/**
 * Parse the lower-half exponent from a text field: empty means "same as n"
 * (null); otherwise clamped to the range seen in real data (0.5 .. 50).
 */
export function parseLowerExponent(text: string): number | null {
  if (text.trim() === "") return null;
  const value = Number.parseFloat(text);
  if (!Number.isFinite(value)) return null;
  return Math.max(0.5, Math.min(50, value));
}
