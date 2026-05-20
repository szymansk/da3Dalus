"use client";

import { Info } from "lucide-react";

/**
 * gh-581: Banner surfaced on the workbench when the active aeroplane has
 * no horizontal tail (`is_tailless = true` in the computation context).
 *
 * Explains the design implications:
 *  - Tail-volume sizing is not applicable.
 *  - Longitudinal trim must come from sweep + washout + reflex airfoil
 *    (Apogee's hybrid approach is the preferred default).
 *  - The static-margin corridor is tighter (5–10 % MAC, default 7.5 %)
 *    per #579 — this is a dynamic-stability / control-power floor, not
 *    a static-aerodynamic limit (C_m,q pitch damping is much smaller
 *    without a tail moment arm).
 *  - CG envelope is ~50 % narrower; mass-fixed items should mount on the
 *    CG axis.
 */
export function TaillessBanner() {
  return (
    <div
      role="status"
      data-testid="tailless-banner"
      className="flex items-start gap-2 rounded-full bg-orange-500/15 px-3 py-1.5 text-orange-400"
    >
      <Info size={12} className="mt-0.5 shrink-0" />
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] leading-snug">
        <span className="font-semibold">Tailless configuration</span> — Tail-volume
        sizing not applicable. Pitch trim via sweep + washout, reflex airfoil,
        or hybrid (preferred). SM target 5–10 % MAC (narrower CG envelope than
        conventional, ~50 % less travel; mount mass-fixed items on CG axis).
      </span>
    </div>
  );
}
