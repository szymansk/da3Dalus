import { API_BASE } from "@/lib/fetcher";

/** Explicit role of a wing (GH-1187). The type follows the function, not the position. */
export type SurfaceType =
  | "main_wing"
  | "horizontal_tail"
  | "vertical_tail"
  | "v_tail"
  | "canard"
  | "tandem_wing"
  | "winglet";

export const SURFACE_TYPES: readonly SurfaceType[] = [
  "main_wing",
  "horizontal_tail",
  "vertical_tail",
  "v_tail",
  "canard",
  "tandem_wing",
  "winglet",
];

export const SURFACE_TYPE_LABELS: Record<SurfaceType, string> = {
  main_wing: "Main wing",
  horizontal_tail: "Horizontal tail",
  vertical_tail: "Vertical tail",
  v_tail: "V-tail",
  canard: "Canard",
  tandem_wing: "Tandem wing",
  winglet: "Winglet",
};

export const SURFACE_TYPE_HINTS: Record<SurfaceType, string> = {
  main_wing: "The wing that carries the aircraft weight. Exactly one per aeroplane.",
  horizontal_tail: "Aft pitch-stabilising surface (stabiliser and elevator).",
  vertical_tail: "Fin and rudder for directional stability.",
  v_tail: "Two canted surfaces doing the job of horizontal and vertical tail.",
  canard: "Forward pitch surface ahead of the main wing.",
  tandem_wing: "Second lifting wing in tandem with the main wing.",
  winglet: "Small surface at a wing tip that reduces induced drag.",
};

export function surfaceTypeLabel(value: string | null | undefined): string {
  if (!value) return "Unknown";
  return SURFACE_TYPE_LABELS[value as SurfaceType] ?? value;
}

export const PROPOSED_TOOLTIP =
  "This role was proposed from the wing's name and size. Confirm it or choose the correct role.";

export interface SurfaceTypePatch {
  surface_type: SurfaceType;
  former_main_becomes?: SurfaceType;
}

/** Extract a human readable message from a FastAPI error body. */
export function extractErrorDetail(body: string, status: number): string {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join("; ");
    }
  } catch {
    // not JSON
  }
  return body || `Request failed (${status})`;
}

/** PATCH the wing's role; marks it confirmed on the backend. Throws Error(detail) on failure. */
export async function patchSurfaceType(
  aeroplaneId: string,
  wingName: string,
  body: SurfaceTypePatch,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(wingName)}/surface-type`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(extractErrorDetail(text, res.status));
  }
}
