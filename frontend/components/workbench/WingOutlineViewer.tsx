"use client";

import { useEffect, useRef, useState } from "react";
import type { Wing } from "@/hooks/useWings";
import type { Fuselage } from "@/hooks/useFuselage";
import { API_BASE } from "@/lib/fetcher";

interface WingOutlineViewerProps {
  wings: Wing[];
  fuselages: Fuselage[];
  visibleWings: Set<string>;
  visibleFuselages: Set<string>;
}

/** Cache for airfoil coordinate data */
const airfoilCache: Record<string, { x: number[]; y: number[] } | null> = {};

async function fetchAirfoilCoords(airfoilName: string): Promise<{ x: number[]; y: number[] } | null> {
  // Normalize: extract filename stem from paths like "/path/to/mh32.dat"
  const stem = airfoilName.replace(/\.dat$/i, "").split("/").pop() ?? airfoilName;
  if (stem in airfoilCache) return airfoilCache[stem];
  try {
    const res = await fetch(`${API_BASE}/airfoils/${encodeURIComponent(stem)}/coordinates`);
    if (!res.ok) { airfoilCache[stem] = null; return null; }
    const data = await res.json();
    airfoilCache[stem] = data;
    return data;
  } catch {
    airfoilCache[stem] = null;
    return null;
  }
}

/** Build 3D airfoil contour traces at each cross-section station */
async function buildAirfoilTraces(wing: Wing, color: string): Promise<Plotly.Data[]> {
  const traces: Plotly.Data[] = [];

  for (const xsec of wing.x_secs) {
    const coords = await fetchAirfoilCoords(xsec.airfoil);
    if (!coords) continue;

    const chord = xsec.chord;
    const [leX, leY, leZ] = xsec.xyz_le;
    const twistRad = (xsec.twist ?? 0) * Math.PI / 180;
    const cosT = Math.cos(twistRad);
    const sinT = Math.sin(twistRad);

    // Transform airfoil coordinates: scale by chord, rotate by twist around LE, translate to LE position
    const ax: number[] = [];
    const ay: number[] = [];
    const az: number[] = [];

    for (let i = 0; i < coords.x.length; i++) {
      const px = coords.x[i] * chord;  // chordwise (x)
      const pz = coords.y[i] * chord;  // thickness (z)
      // Apply twist rotation around LE (in xz plane)
      const rx = px * cosT + pz * sinT;
      const rz = -px * sinT + pz * cosT;
      ax.push(leX + rx);
      ay.push(leY);
      az.push(leZ + rz);
    }

    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: ax, y: ay, z: az,
      line: { color, width: 1.5 },
      showlegend: false,
      hoverinfo: "skip",
    });
  }

  // Mirror if symmetric
  if (wing.symmetric) {
    const mirrorTraces = traces.map((t) => ({
      ...t,
      y: (t.y as number[]).map((v: number) => -v),
    }));
    traces.push(...mirrorTraces);
  }

  return traces;
}

/** Build leading/trailing edge + cross-section traces for a wing. */
function buildWingTraces(wing: Wing, color: string) {
  const traces: Plotly.Data[] = [];
  const xsecs = wing.x_secs;
  if (xsecs.length < 2) return traces;

  // Leading edge line
  const leX = xsecs.map((xs) => xs.xyz_le[0]);
  const leY = xsecs.map((xs) => xs.xyz_le[1]);
  const leZ = xsecs.map((xs) => xs.xyz_le[2]);

  // Trailing edge line (LE + chord along x)
  const teX = xsecs.map((xs) => xs.xyz_le[0] + xs.chord);
  const teY = xsecs.map((xs) => xs.xyz_le[1]);
  const teZ = xsecs.map((xs) => xs.xyz_le[2]);

  // Leading edge
  traces.push({
    type: "scatter3d",
    mode: "lines",
    x: leX, y: leY, z: leZ,
    line: { color, width: 3 },
    name: `${wing.name} LE`,
    showlegend: false,
    hoverinfo: "skip",
  });

  // Trailing edge
  traces.push({
    type: "scatter3d",
    mode: "lines",
    x: teX, y: teY, z: teZ,
    line: { color, width: 3 },
    name: `${wing.name} TE`,
    showlegend: false,
    hoverinfo: "skip",
  });

  // Root chord line
  traces.push({
    type: "scatter3d",
    mode: "lines",
    x: [leX[0], teX[0]],
    y: [leY[0], teY[0]],
    z: [leZ[0], teZ[0]],
    line: { color, width: 2 },
    showlegend: false,
    hoverinfo: "skip",
  });

  // Tip chord line
  const last = xsecs.length - 1;
  traces.push({
    type: "scatter3d",
    mode: "lines",
    x: [leX[last], teX[last]],
    y: [leY[last], teY[last]],
    z: [leZ[last], teZ[last]],
    line: { color, width: 2 },
    showlegend: false,
    hoverinfo: "skip",
  });

  // Cross-section lines at each station
  for (let i = 1; i < xsecs.length - 1; i++) {
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: [leX[i], teX[i]],
      y: [leY[i], teY[i]],
      z: [leZ[i], teZ[i]],
      line: { color, width: 1, dash: "dot" },
      showlegend: false,
      hoverinfo: "skip",
    });
  }

  // TED hinge lines (colored differently)
  for (let i = 0; i < xsecs.length; i++) {
    const ted = xsecs[i].trailing_edge_device ?? xsecs[i].control_surface;
    if (!ted) continue;
    const relChord = (ted as Record<string, unknown>).rel_chord_root as number | undefined;
    if (relChord == null) continue;

    const hingeX = xsecs[i].xyz_le[0] + xsecs[i].chord * (1 - relChord);
    const teXi = xsecs[i].xyz_le[0] + xsecs[i].chord;

    // Find the next xsec that also has a TED for the hinge line extent
    const nextI = i + 1 < xsecs.length ? i + 1 : i;
    const nextTed = xsecs[nextI]?.trailing_edge_device ?? xsecs[nextI]?.control_surface;
    const nextRelChord = nextTed ? ((nextTed as Record<string, unknown>).rel_chord_tip as number ?? relChord) : relChord;
    const nextHingeX = xsecs[nextI].xyz_le[0] + xsecs[nextI].chord * (1 - nextRelChord);

    // Hinge line
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: [hingeX, nextHingeX],
      y: [xsecs[i].xyz_le[1], xsecs[nextI].xyz_le[1]],
      z: [xsecs[i].xyz_le[2], xsecs[nextI].xyz_le[2]],
      line: { color: "#30A46C", width: 3 },
      name: `TED`,
      showlegend: false,
      hoverinfo: "skip",
    });

    // TED area (filled between hinge and TE)
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: [hingeX, teXi, xsecs[nextI].xyz_le[0] + xsecs[nextI].chord, nextHingeX, hingeX],
      y: [xsecs[i].xyz_le[1], xsecs[i].xyz_le[1], xsecs[nextI].xyz_le[1], xsecs[nextI].xyz_le[1], xsecs[i].xyz_le[1]],
      z: [xsecs[i].xyz_le[2], xsecs[i].xyz_le[2], xsecs[nextI].xyz_le[2], xsecs[nextI].xyz_le[2], xsecs[i].xyz_le[2]],
      line: { color: "#30A46C", width: 1 },
      showlegend: false,
      hoverinfo: "skip",
    });
  }

  // Mirror if symmetric
  if (wing.symmetric) {
    const mirrorTraces = traces.map((t) => ({
      ...t,
      y: (t.y as number[]).map((v: number) => -v),
      name: undefined,
    }));
    traces.push(...mirrorTraces);
  }

  return traces;
}

/** Build superellipse cross-section traces for a fuselage. */
function buildFuselageTraces(fuselage: Fuselage, color: string) {
  const traces: Plotly.Data[] = [];
  const xsecs = fuselage.x_secs;
  if (xsecs.length < 2) return traces;

  // Centerline
  traces.push({
    type: "scatter3d",
    mode: "lines",
    x: xsecs.map((xs) => xs.xyz[0]),
    y: xsecs.map((xs) => xs.xyz[1]),
    z: xsecs.map((xs) => xs.xyz[2]),
    line: { color, width: 2 },
    showlegend: false,
    hoverinfo: "skip",
  });

  // Cross-section outlines
  const nPts = 32;
  for (const xs of xsecs) {
    const cx: number[] = [];
    const cy: number[] = [];
    const cz: number[] = [];
    for (let j = 0; j <= nPts; j++) {
      const theta = (2 * Math.PI * j) / nPts;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);
      // Superellipse: |y/a|^n + |z/b|^n = 1
      const r_y = xs.a * Math.sign(cosT) * Math.pow(Math.abs(cosT), 2 / xs.n);
      const r_z = xs.b * Math.sign(sinT) * Math.pow(Math.abs(sinT), 2 / xs.n);
      cx.push(xs.xyz[0]);
      cy.push(xs.xyz[1] + r_y);
      cz.push(xs.xyz[2] + r_z);
    }
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: cx, y: cy, z: cz,
      line: { color, width: 1.5 },
      showlegend: false,
      hoverinfo: "skip",
    });
  }

  // Longitudinal lines (top, bottom, sides)
  for (const angle of [0, Math.PI / 2, Math.PI, 3 * Math.PI / 2]) {
    const lx: number[] = [];
    const ly: number[] = [];
    const lz: number[] = [];
    for (const xs of xsecs) {
      const cosT = Math.cos(angle);
      const sinT = Math.sin(angle);
      const r_y = xs.a * Math.sign(cosT) * Math.pow(Math.abs(cosT + 1e-10), 2 / xs.n);
      const r_z = xs.b * Math.sign(sinT) * Math.pow(Math.abs(sinT + 1e-10), 2 / xs.n);
      lx.push(xs.xyz[0]);
      ly.push(xs.xyz[1] + r_y);
      lz.push(xs.xyz[2] + r_z);
    }
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: lx, y: ly, z: lz,
      line: { color, width: 1, dash: "dot" },
      showlegend: false,
      hoverinfo: "skip",
    });
  }

  return traces;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Plotly = any;

export function WingOutlineViewer({ wings, fuselages, visibleWings, visibleFuselages }: WingOutlineViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotlyRef = useRef<Plotly>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    async function render() {
      if (!containerRef.current) return;
      setLoading(true);

      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed) return;
      plotlyRef.current = Plotly;

      const traces: Plotly.Data[] = [];

      for (const wing of wings) {
        if (!visibleWings.has(wing.name)) continue;
        traces.push(...buildWingTraces(wing, "#FF8400"));
        // Fetch and render airfoil contours at each xsec station
        const airfoilTraces = await buildAirfoilTraces(wing, "#FF840080");
        traces.push(...airfoilTraces);
      }

      for (const fuse of fuselages) {
        if (!visibleFuselages.has(fuse.name)) continue;
        traces.push(...buildFuselageTraces(fuse, "#B8B9B6"));
      }

      const layout = {
        paper_bgcolor: "#17171A",
        plot_bgcolor: "#17171A",
        scene: {
          xaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A", color: "#7A7B78", title: "x" },
          yaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A", color: "#7A7B78", title: "y" },
          zaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A", color: "#7A7B78", title: "z" },
          aspectmode: "data",
          bgcolor: "#17171A",
        },
        margin: { l: 0, r: 0, t: 0, b: 0 },
        showlegend: false,
      };

      const config = { displayModeBar: false, responsive: true };

      await Plotly.newPlot(containerRef.current, traces, layout, config);
      setLoading(false);
    }

    render();

    return () => {
      disposed = true;
      if (containerRef.current && plotlyRef.current) {
        try { plotlyRef.current.purge(containerRef.current); } catch { /* ok */ }
      }
    };
  }, [wings, fuselages, visibleWings, visibleFuselages]);

  return (
    <div className="relative h-full w-full">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-card-muted/80">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Loading preview…
          </span>
        </div>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
