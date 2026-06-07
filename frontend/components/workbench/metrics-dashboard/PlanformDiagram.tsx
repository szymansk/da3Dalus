"use client";

// Click-dummy (#881) — schematic top-view planform with dimension annotations,
// like a technical drawing. SVG draws only the shapes + dimension lines; the
// labels are real HTML overlaid on top (crisp text at any band height, instead
// of tiny down-scaled SVG <text>). The container is locked to the SVG's aspect
// ratio so HTML percentages map 1:1 onto viewBox coordinates.
//
// Real implementation should drive this from the ACTUAL design's top-view
// outline (WingOutlineViewer / ortho render) so flying-wings and canards are
// correct — this is only a stand-in.

const VBW = 240;
const VBH = 132;
const pct = (x: number, total: number) => `${(x / total) * 100}%`;

export type PlanformType = "conventional" | "canard" | "flyingwing";

export function PlanformDiagram({
  bRef, mac, sRef, ar, type = "conventional", annotate = false,
}: {
  readonly bRef: string; readonly mac: string; readonly sRef: string; readonly ar: string;
  readonly type?: PlanformType; readonly annotate?: boolean;
}) {
  const showTail = type !== "flyingwing";
  const tailFront = type === "canard";
  const wing = "24,58 120,46 216,58 216,72 120,82 24,72";
  const tail = tailFront ? "96,18 144,18 138,26 102,26" : "92,98 148,98 142,106 98,106";

  return (
    <div className="relative mx-auto aspect-[240/132] h-full">
      <svg viewBox={`0 0 ${VBW} ${VBH}`} preserveAspectRatio="xMidYMid meet" className="absolute inset-0 h-full w-full" role="img" aria-label="Top-view planform with dimensions">
        <defs>
          <marker id="pf-arrow" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--color-muted-foreground)" />
          </marker>
        </defs>
        {type !== "flyingwing" && (
          <rect x="116" y="12" width="8" height="94" rx="4" fill="var(--color-card-muted)" stroke="var(--color-border-strong)" strokeWidth="1" />
        )}
        <polygon points={wing} fill="var(--color-primary)" fillOpacity="0.16" stroke="var(--color-primary)" strokeWidth="1.4" />
        {showTail && <polygon points={tail} fill="var(--color-foreground)" fillOpacity="0.08" stroke="var(--color-border-strong)" strokeWidth="1" />}
        {annotate && (
          <g>
            {/* span B_ref */}
            <line x1="24" y1="118" x2="216" y2="118" stroke="var(--color-muted-foreground)" strokeWidth="1" markerStart="url(#pf-arrow)" markerEnd="url(#pf-arrow)" />
            <line x1="24" y1="72" x2="24" y2="122" stroke="var(--color-subtle-foreground)" strokeWidth="0.7" />
            <line x1="216" y1="72" x2="216" y2="122" stroke="var(--color-subtle-foreground)" strokeWidth="0.7" />
            {/* MAC chord (left semi-span) */}
            <line x1="72" y1="51" x2="72" y2="78" stroke="var(--color-primary)" strokeWidth="1.1" markerStart="url(#pf-arrow)" markerEnd="url(#pf-arrow)" />
          </g>
        )}
      </svg>

      {annotate && (
        <div className="pointer-events-none absolute inset-0 font-[family-name:var(--font-geist-mono)]">
          <Label x={120} y={126} anchor="center" className="text-foreground">B_ref {bRef} m</Label>
          <Label x={68} y={64} anchor="end" className="text-primary">MAC {mac} m</Label>
          <Label x={150} y={40} anchor="start" className="text-muted-foreground">S_ref {sRef} m²</Label>
          <Label x={150} y={92} anchor="start" className="text-muted-foreground">AR {ar}</Label>
        </div>
      )}
    </div>
  );
}

const ANCHOR_TX: Record<"start" | "center" | "end", string> = { start: "0", center: "-50%", end: "-100%" };

function Label({
  x, y, anchor, className, children,
}: {
  readonly x: number; readonly y: number; readonly anchor: "start" | "center" | "end";
  readonly className: string; readonly children: React.ReactNode;
}) {
  const tx = ANCHOR_TX[anchor];
  return (
    <span
      className={`absolute whitespace-nowrap text-[11px] leading-none ${className}`}
      style={{ left: pct(x, VBW), top: pct(y, VBH), transform: `translate(${tx}, -50%)` }}
    >
      {children}
    </span>
  );
}
