"use client";

// Click-dummy (#881) — schematic top-view planform with dimension annotations,
// like a technical drawing. In the real implementation this should be driven by
// the ACTUAL design's top-view outline (e.g. WingOutlineViewer / an ortho render)
// so flying-wings and canards render correctly — this SVG is only a stand-in.

export type PlanformType = "conventional" | "canard" | "flyingwing";

export function PlanformDiagram({
  bRef, mac, sRef, ar, type = "conventional", annotate = false,
}: {
  readonly bRef: string; readonly mac: string; readonly sRef: string; readonly ar: string;
  readonly type?: PlanformType; readonly annotate?: boolean;
}) {
  const showTail = type !== "flyingwing";
  const tailFront = type === "canard"; // canard surface ahead of the wing

  // main wing polygon (symmetric trapezoid), LE then TE reversed
  const wing = "24,58 120,46 216,58 216,72 120,82 24,72";
  // small stabiliser trapezoid, placed rear (or front for canard)
  const tail = tailFront ? "96,18 144,18 138,26 102,26" : "92,98 148,98 142,106 98,106";

  return (
    <svg viewBox="0 0 240 132" className="h-full max-h-[124px] w-auto" role="img" aria-label="Top-view planform with dimensions">
      <defs>
        <marker id="pf-arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--color-subtle-foreground)" />
        </marker>
      </defs>

      {/* fuselage */}
      {type !== "flyingwing" && (
        <rect x="116" y="12" width="8" height="94" rx="4" fill="var(--color-card-muted)" stroke="var(--color-border-strong)" strokeWidth="1" />
      )}
      {/* main wing */}
      <polygon points={wing} fill="var(--color-primary)" fillOpacity="0.14" stroke="var(--color-primary)" strokeWidth="1.2" />
      {/* stabiliser */}
      {showTail && <polygon points={tail} fill="var(--color-foreground)" fillOpacity="0.08" stroke="var(--color-border-strong)" strokeWidth="1" />}

      {annotate && (
        <g className="font-[family-name:var(--font-geist-mono)]">
          {/* span B_ref */}
          <line x1="24" y1="120" x2="216" y2="120" stroke="var(--color-subtle-foreground)" strokeWidth="0.8" markerStart="url(#pf-arrow)" markerEnd="url(#pf-arrow)" />
          <line x1="24" y1="72" x2="24" y2="124" stroke="var(--color-subtle-foreground)" strokeWidth="0.6" />
          <line x1="216" y1="72" x2="216" y2="124" stroke="var(--color-subtle-foreground)" strokeWidth="0.6" />
          <text x="120" y="118" textAnchor="middle" fontSize="7" fill="var(--color-foreground)">B_ref {bRef} m</text>

          {/* MAC chord at ~mid semi-span (left) */}
          <line x1="72" y1="52" x2="72" y2="77" stroke="var(--color-primary)" strokeWidth="0.9" markerStart="url(#pf-arrow)" markerEnd="url(#pf-arrow)" />
          <text x="66" y="67" textAnchor="end" fontSize="7" fill="var(--color-primary)">MAC {mac} m</text>

          {/* area + AR labels */}
          <text x="150" y="42" fontSize="7" fill="var(--color-muted-foreground)">S_ref {sRef} m²</text>
          <text x="150" y="92" fontSize="7" fill="var(--color-muted-foreground)">AR {ar}</text>
        </g>
      )}
    </svg>
  );
}
