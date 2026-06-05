/**
 * 2D airfoil proxy chart helpers (gh-841).
 *
 * Computes cl^1.5/cd (endurance indicator) and cl/cd (range/glide indicator)
 * vs cl from a 2D airfoil polar.  These are SECTION-level metrics, NOT the
 * aircraft polar — callers must label charts clearly to avoid confusion.
 *
 * All functions are pure with no side effects, enabling isolated unit tests.
 */

export interface AirfoilProxyPoint {
  cl: number;
  /** cl^1.5 / cd — section endurance indicator */
  cl15OverCd: number;
  /** cl / cd — section range / glide indicator */
  clOverCd: number;
}

/**
 * Build proxy chart data from parallel cl/cd arrays.
 *
 * Filters out:
 * - null / non-finite values (from NeuralFoil degenerate outputs)
 * - non-positive cd (unphysical, would invert metrics)
 * - non-positive cl (negative CL range not meaningful for endurance/glide)
 */
export function buildAirfoilProxyChartData(
  cl: (number | null)[],
  cd: (number | null)[],
): AirfoilProxyPoint[] {
  const result: AirfoilProxyPoint[] = [];
  const n = Math.min(cl.length, cd.length);
  for (let i = 0; i < n; i++) {
    const c = cl[i];
    const d = cd[i];
    if (
      c == null ||
      d == null ||
      !isFinite(c) ||
      !isFinite(d) ||
      c <= 0 ||
      d <= 0
    ) {
      continue;
    }
    result.push({
      cl: c,
      cl15OverCd: Math.pow(c, 1.5) / d,
      clOverCd: c / d,
    });
  }
  // Sort by cl ascending so lines are drawn left-to-right
  result.sort((a, b) => a.cl - b.cl);
  return result;
}

/**
 * Extract the peak cl/cd value and its cl from proxy data.
 * Returns null when data is empty.
 */
export function findPeakClOverCd(
  data: AirfoilProxyPoint[],
): { cl: number; clOverCd: number } | null {
  if (data.length === 0) return null;
  let peak = data[0];
  for (const pt of data) {
    if (pt.clOverCd > peak.clOverCd) peak = pt;
  }
  return { cl: peak.cl, clOverCd: peak.clOverCd };
}

/**
 * Extract the peak cl^1.5/cd value and its cl from proxy data.
 * Returns null when data is empty.
 */
export function findPeakCl15OverCd(
  data: AirfoilProxyPoint[],
): { cl: number; cl15OverCd: number } | null {
  if (data.length === 0) return null;
  let peak = data[0];
  for (const pt of data) {
    if (pt.cl15OverCd > peak.cl15OverCd) peak = pt;
  }
  return { cl: peak.cl, cl15OverCd: peak.cl15OverCd };
}
