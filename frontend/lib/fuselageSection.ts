/**
 * Fuselage sections: the super-ellipse (gh-1157) and the optional point contour (gh-1349).
 *
 * Upper half (z >= 0): |y/a|^n + |z/b|^n = 1.
 * Lower half (z < 0):  same with `n_lower`, falling back to `n` when unset.
 * `a` and `b` are half-axes in metres.
 *
 * A section with a `contour` is drawn from the contour: it wins for display and
 * CAD, while a/b/n/n_lower stay as the fit the aerodynamic solvers use.
 */
export interface SuperEllipseSection {
  a: number;
  b: number;
  n: number;
  n_lower?: number | null;
}

/** One contour point `[y, z]`, metres, relative to the section centre `xyz`. */
export type ContourPoint = [number, number];

/** A fuselage section as the API returns it, with its optional contour. */
export interface FuselageSection extends SuperEllipseSection {
  /**
   * gh-1349: measured full outline as a closed loop, counter-clockwise, the
   * closing segment implicit (first point not repeated); no symmetry assumed.
   * `null`/absent: the super-ellipse.
   */
  contour?: ContourPoint[] | null;
}

/** An outline point as an offset from the section centre. */
export interface SectionPoint {
  y: number;
  z: number;
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

/** Number of contour points of a section, `null` when it has no contour. */
export function contourPointCount(xs: FuselageSection): number | null {
  return xs.contour ? xs.contour.length : null;
}

/**
 * Closed outline of a section as offsets from its centre.
 *
 * With a contour: the contour's own points as given, then its first point
 * again to close the loop: N + 1 points, never mirrored or resampled, so the
 * sample count is ignored. Without: today's super-ellipse at
 * theta = 2*pi*j/samples, j = 0..samples.
 */
export function sectionOutline(xs: FuselageSection, samples: number): SectionPoint[] {
  const contour = xs.contour;
  if (contour && contour.length > 0) {
    const points = contour.map(([y, z]) => ({ y, z }));
    return [...points, points[0]];
  }
  const points: SectionPoint[] = [];
  for (let j = 0; j <= samples; j++) {
    points.push(sectionOffset(xs, (2 * Math.PI * j) / samples));
  }
  return points;
}

/**
 * First point of a non-empty `contour` with the largest `score` (ties keep the
 * earlier point); callers pass only contours with at least one point.
 */
function extremePoint(contour: ContourPoint[], score: (p: ContourPoint) => number): SectionPoint {
  const [first, ...rest] = contour;
  const [y, z] = rest.reduce((best, p) => (score(p) > score(best) ? p : best), first);
  return { y, z };
}

/**
 * The four points the longitudinal lines run through: right side, top, left
 * side, bottom. A contour gives its points of largest y, largest z, smallest y
 * and smallest z (it may be asymmetric); a super-ellipse its points at 0, 90,
 * 180 and 270 degrees.
 */
export function sectionExtremes(xs: FuselageSection): {
  right: SectionPoint;
  top: SectionPoint;
  left: SectionPoint;
  bottom: SectionPoint;
} {
  const contour = xs.contour;
  if (contour && contour.length > 0) {
    return {
      right: extremePoint(contour, ([y]) => y),
      top: extremePoint(contour, ([, z]) => z),
      left: extremePoint(contour, ([y]) => -y),
      bottom: extremePoint(contour, ([, z]) => -z),
    };
  }
  return {
    right: sectionOffset(xs, 0),
    top: sectionOffset(xs, Math.PI / 2),
    left: sectionOffset(xs, Math.PI),
    bottom: sectionOffset(xs, (3 * Math.PI) / 2),
  };
}

/** Tree/label text: the exponent label, plus "contour (N points)" when present. */
export function sectionShapeLabel(xs: FuselageSection): string {
  const count = contourPointCount(xs);
  const exponents = sectionExponentLabel(xs);
  return count == null ? exponents : `${exponents} \u00B7 contour (${count} points)`;
}

/**
 * Warning shown while a/b/n of a section with a contour are edited: the contour
 * wins for display and CAD, the parameters only feed the aerodynamic analysis.
 */
export function contourWinsWarning(xs: FuselageSection): string | null {
  const count = contourPointCount(xs);
  if (count == null) return null;
  return (
    `This section has a contour (${count} points). The contour wins for display and CAD; ` +
    "a, b and n are only the fit the aerodynamic analysis uses, so editing them does not change " +
    "the drawn or built shape."
  );
}

/**
 * Mirror a section across the XZ plane (y -> -y) for the mirrored copy of a
 * `symmetric` body (gh-1360). A contour is mirrored point by point as (-y, z)
 * in reversed order, so the loop stays counter-clockwise; `0 - y` avoids -0.
 * Same rule as the backend's `_mirror_contour_y`.
 */
export function mirrorSectionY<T extends FuselageSection & { xyz: number[] }>(xs: T): T {
  const mirrored: T = { ...xs, xyz: [xs.xyz[0], -xs.xyz[1], xs.xyz[2]] };
  if (xs.contour) {
    mirrored.contour = xs.contour
      .map(([y, z]): ContourPoint => [0 - y, z])
      .reverse();
  }
  return mirrored;
}
