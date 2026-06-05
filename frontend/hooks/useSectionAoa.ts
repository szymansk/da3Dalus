"use client";

import useSWR from "swr";

// ---------------------------------------------------------------------------
// Types — mirror backend SectionAoaResponse schema (gh-840)
// ---------------------------------------------------------------------------

export interface SectionAoaPoint {
  /** Spanwise position [m] */
  y_m: number;
  /** Panel chord [m] */
  chord_m: number;
  /** Section lift coefficient (includes induced downwash) */
  cl: number;
  /** Geometric AoA = trim α + wing incidence + twist(y)  [deg] */
  alpha_geometric_deg: number;
  /** Effective AoA = geometric − induced  [deg] */
  alpha_effective_deg: number;
  /** Induced downwash angle [deg] */
  induced_angle_deg: number;
}

export interface SectionAoaData {
  aeroplane_id: string;
  wing_name: string;
  operating_point_id: number | null;
  sections: SectionAoaPoint[];
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * SWR hook for per-section world AoA endpoint (gh-840).
 *
 * Fetches GET /aeroplanes/{aeroplaneId}/wings/{wingName}/section-aoa
 * with an optional stored operating_point_id.
 *
 * Returns null when the aeroplane or wing has no data / insufficient
 * operating point (HTTP 422 / 404).  Callers guard on null.
 */
export function useSectionAoa(
  aeroplaneId: string | null,
  wingName: string | null | undefined,
  operatingPointId?: number | null,
): {
  data: SectionAoaData | null;
  isLoading: boolean;
  error: Error | null;
} {
  const queryParam =
    operatingPointId != null ? `?operating_point_id=${operatingPointId}` : "";

  const url =
    aeroplaneId && wingName
      ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/wings/${encodeURIComponent(wingName)}/section-aoa${queryParam}`
      : null;

  const { data, error, isLoading } = useSWR<SectionAoaData | null>(
    url,
    async (path: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"}${path}`,
      );
      if (res.status === 404 || res.status === 422 || res.status === 503) {
        // Wing/plane not found, insufficient context, or aero not available
        return null;
      }
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${body}`);
      }
      return res.json() as Promise<SectionAoaData>;
    },
    { revalidateOnFocus: false },
  );

  return {
    data: data ?? null,
    error: error ?? null,
    isLoading,
  };
}

// ---------------------------------------------------------------------------
// Helpers (pure, testable without hooks)
// ---------------------------------------------------------------------------

/**
 * Find the section closest to a given spanwise fraction (0=root, 1=tip).
 * Returns null when sections is empty.
 */
export function findSectionAtFraction(
  sections: SectionAoaPoint[],
  fraction: number,
): SectionAoaPoint | null {
  if (sections.length === 0) return null;
  // Use only positive-y (starboard) sections for a symmetric wing
  const posSections = sections.filter((s) => s.y_m >= 0);
  if (posSections.length === 0) return sections[0];

  const maxY = Math.max(...posSections.map((s) => s.y_m));
  const targetY = fraction * maxY;

  let closest = posSections[0];
  let minDist = Math.abs(posSections[0].y_m - targetY);
  for (const s of posSections) {
    const d = Math.abs(s.y_m - targetY);
    if (d < minDist) {
      minDist = d;
      closest = s;
    }
  }
  return closest;
}

/**
 * Get the section for the currently selected cross-section index.
 * The cross-section index maps to a spanwise position; we pick the
 * closest positive-y panel.
 */
export function sectionForXsecIndex(
  sections: SectionAoaPoint[],
  xsecIndex: number,
  segmentCount: number,
): SectionAoaPoint | null {
  if (sections.length === 0 || segmentCount <= 0) return null;
  // Map xsec index to spanwise fraction: 0 = root, 1 = tip
  const fraction = segmentCount > 1 ? xsecIndex / (segmentCount - 1) : 0;
  return findSectionAtFraction(sections, fraction);
}
