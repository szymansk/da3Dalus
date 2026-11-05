"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";
import type { ContourPoint } from "@/lib/fuselageSection";
import type { BodyRole } from "@/lib/bodyRole";

export interface FuselageXSec {
  xyz: number[];
  a: number;
  b: number;
  n: number;
  /** gh-1157: exponent of the lower half (z < 0); null/absent = same as `n`. */
  n_lower?: number | null;
  /**
   * gh-1349: measured full outline as a closed loop, [y, z] in metres relative
   * to `xyz`, counter-clockwise, first point not repeated. Wins for display and
   * CAD; null/absent = the super-ellipse. Read-only in the UI (exporter-written).
   */
  contour?: ContourPoint[] | null;
}

export interface Fuselage {
  name: string;
  x_secs: FuselageXSec[];
  /**
   * gh-715: XZ-mirror flag. When true, the viewer renders a mirrored
   * copy (y → -y) so paired sub-fuselages (landing-gear struts,
   * wheel-fairings) show on both sides. Defaults to false for the
   * main fuselage which sits on the symmetry plane itself.
   */
  symmetric?: boolean;
  /** gh-1355: what the body is; absent = fuselage (the format's default). */
  role?: BodyRole;
  /** gh-1355: name of the body this one sits on; null/absent = none. A canopy has one. */
  attached_to?: string | null;
  /**
   * gh-729: relative path to the per-geom STEP file exported at
   * OpenVSP-import time. ``null`` for CAD-created fuselages.
   * Frontend uses this only as a "has STEP?" flag — the actual
   * download goes through ``GET /aeroplanes/{id}/fuselages/{name}/step``.
   */
  step_path?: string | null;
  /**
   * gh-731: relative path to the sewed closed-Solid STEP file
   * produced from ``step_path`` at OpenVSP-import time. ``null``
   * when sewing failed or the fuselage wasn't VSP-imported. Frontend
   * uses this only as a "has Solid STEP?" flag — download goes
   * through ``GET /aeroplanes/{id}/fuselages/{name}/solid_step``.
   */
  solid_step_path?: string | null;
}

/**
 * Load full Fuselage data for ALL fuselage names in parallel.
 */
export function useAllFuselageData(aeroplaneId: string | null, fuselageNames: string[]) {
  const key = aeroplaneId && fuselageNames.length > 0
    ? `all-fuselages:${aeroplaneId}:${fuselageNames.join(",")}`
    : null;

  const { data, error, isLoading, mutate } = useSWR<Fuselage[]>(
    key,
    async () => {
      const results = await Promise.all(
        fuselageNames.map(async (name) => {
          const res = await fetch(
            `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(name)}`,
          );
          if (!res.ok) return null;
          return res.json() as Promise<Fuselage>;
        }),
      );
      return results.filter((f): f is Fuselage => f !== null);
    },
  );

  return { fuselages: data ?? [], error, isLoading, mutate };
}

export function useFuselage(aeroplaneId: string | null, fuselageName: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Fuselage>(
    aeroplaneId && fuselageName
      ? `/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}`
      : null,
    fetcher,
  );

  async function updateXSec(index: number, xsec: FuselageXSec): Promise<void> {
    if (!aeroplaneId || !fuselageName) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}/cross_sections/${index}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(xsec),
      },
    );
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Update xsec failed: ${res.status} ${body}`);
    }
    mutate();
  }

  /** gh-1355: change role and parent; the update replaces the whole body, so it sends it all. */
  async function saveBody(fields: { role: BodyRole; attached_to: string | null }): Promise<void> {
    if (!aeroplaneId || !fuselageName || !data) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, ...fields }),
      },
    );
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Update failed: ${res.status} ${body}`);
    }
    mutate();
  }

  return {
    fuselage: data ?? null,
    error,
    isLoading,
    mutate,
    updateXSec,
    saveBody,
  };
}
