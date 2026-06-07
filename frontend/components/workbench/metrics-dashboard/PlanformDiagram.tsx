"use client";

import { renderSymbol } from "@/components/workbench/renderSymbol";

// Click-dummy (#881) — schematic top-view planform with dimension annotations
// AND the CG / NP balance markers drawn directly onto the aircraft (CG and NP
// are longitudinal stations, so they sit along the fuselage centreline; the gap
// is the static margin). SVG draws shapes + lines; labels are real HTML overlaid
// on an aspect-locked container so text stays crisp at any band height.
//
// Real implementation should drive this from the ACTUAL design's top-view
// outline (WingOutlineViewer / ortho render) and overlay CG/NP — this is a
// stand-in. CG/NP can be very close (small SM), so leader lines fan the labels
// apart like a real technical drawing.

const VBW = 240;
const VBH = 132;
const ROOT_LE = 46;
const ROOT_CHORD = 36; // root chord length in viewBox units (LE 46 → TE 82)
const pct = (x: number, total: number) => `${(x / total) * 100}%`;

export type PlanformType = "conventional" | "canard" | "flyingwing";

export function PlanformDiagram({
  bRef, mac, sRef, ar, type = "conventional", annotate = false,
  cgFrac, npFrac, sm, smOk = true,
}: {
  readonly bRef: string; readonly mac: string; readonly sRef: string; readonly ar: string;
  readonly type?: PlanformType; readonly annotate?: boolean;
  readonly cgFrac?: number; readonly npFrac?: number; readonly sm?: string; readonly smOk?: boolean;
}) {
  const showTail = type !== "flyingwing";
  const tailFront = type === "canard";
  const wing = "24,58 120,46 216,58 216,72 120,82 24,72";
  const tail = tailFront ? "96,18 144,18 138,26 102,26" : "92,98 148,98 142,106 98,106";

  const hasBalance = cgFrac != null && npFrac != null;
  const yCg = hasBalance ? ROOT_LE + cgFrac * ROOT_CHORD : 0;
  const yNp = hasBalance ? ROOT_LE + npFrac * ROOT_CHORD : 0;
  const smColor = smOk ? "text-success" : "text-amber-400";

  return (
    <div className="relative mx-auto aspect-[240/132] h-full">
      <svg viewBox={`0 0 ${VBW} ${VBH}`} preserveAspectRatio="xMidYMid meet" className="absolute inset-0 h-full w-full" role="img" aria-label="Top-view planform with dimensions and CG/NP">
        <defs>
          <marker id="pf-arrow" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--color-muted-foreground)" />
          </marker>
        </defs>
        {type !== "flyingwing" && (
          <rect x="116" y="12" width="8" height="94" rx="4" fill="var(--color-card-muted)" stroke="var(--color-border-strong)" strokeWidth="1" />
        )}
        <polygon points={wing} fill="var(--color-primary)" fillOpacity="0.14" stroke="var(--color-primary)" strokeWidth="1.4" />
        {showTail && <polygon points={tail} fill="var(--color-foreground)" fillOpacity="0.08" stroke="var(--color-border-strong)" strokeWidth="1" />}

        {/* CG / NP markers on the aircraft centreline */}
        {hasBalance && (
          <g>
            <line x1="105" y1={yNp} x2="135" y2={yNp} stroke="var(--color-muted-foreground)" strokeWidth="1.4" strokeDasharray="3 2" />
            <line x1="105" y1={yCg} x2="135" y2={yCg} stroke="var(--color-primary)" strokeWidth="1.6" />
            {annotate && (
              <>
                {/* leader lines fan the close CG/NP labels apart */}
                <line x1="106" y1={yCg} x2="100" y2={yCg - 9} stroke="var(--color-subtle-foreground)" strokeWidth="0.5" />
                <line x1="106" y1={yNp} x2="100" y2={yNp + 9} stroke="var(--color-subtle-foreground)" strokeWidth="0.5" />
                {/* SM dimension bracket to the right */}
                <line x1="142" y1={yCg} x2="142" y2={yNp} stroke="var(--color-muted-foreground)" strokeWidth="0.8" markerStart="url(#pf-arrow)" markerEnd="url(#pf-arrow)" />
                <line x1="135" y1={yCg} x2="144" y2={yCg} stroke="var(--color-subtle-foreground)" strokeWidth="0.5" />
                <line x1="135" y1={yNp} x2="144" y2={yNp} stroke="var(--color-subtle-foreground)" strokeWidth="0.5" />
              </>
            )}
          </g>
        )}

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
          <Label x={120} y={126} anchor="center" className="text-foreground">{renderSymbol("B_ref")} {bRef} m</Label>
          <Label x={66} y={64} anchor="end" className="text-primary">{renderSymbol("MAC")} {mac} m</Label>
          <Label x={150} y={36} anchor="start" className="text-muted-foreground">{renderSymbol("S_ref")} {sRef} m²</Label>
          <Label x={150} y={96} anchor="start" className="text-muted-foreground">{renderSymbol("AR")} {ar}</Label>
          {hasBalance && (
            <>
              <Label x={98} y={yCg - 9} anchor="end" className="text-primary">CG</Label>
              <Label x={98} y={yNp + 9} anchor="end" className="text-muted-foreground">NP</Label>
              <Label x={147} y={(yCg + yNp) / 2} anchor="start" className={smColor}>SM {sm}</Label>
            </>
          )}
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
