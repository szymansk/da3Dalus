"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, X, Check, Loader2, Maximize2, Minimize2, Plus, Trash2, Play } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";
import { useDialog } from "@/hooks/useDialog";

/** Build Plotly Surface3d traces for a fuselage from xsec dicts */
function buildFuselageSurface(
  xsecs: XSec[],
  color: string,
  opacity: number,
  name: string,
  samples: number = 24,
): { x: number[][]; y: number[][]; z: number[][]; type: string; colorscale: [number, string][]; showscale: boolean; opacity: number; name: string } {
  const xGrid: number[][] = [];
  const yGrid: number[][] = [];
  const zGrid: number[][] = [];

  for (const xsec of xsecs) {
    const xRow: number[] = [];
    const yRow: number[] = [];
    const zRow: number[] = [];
    for (let j = 0; j <= samples; j++) {
      const t = (j / samples) * 2 * Math.PI;
      const cosT = Math.cos(t);
      const sinT = Math.sin(t);
      const r = Math.pow(
        Math.pow(Math.abs(cosT), xsec.n) + Math.pow(Math.abs(sinT), xsec.n),
        -1 / xsec.n,
      );
      xRow.push(xsec.xyz[0]);
      yRow.push(xsec.xyz[1] + xsec.a * r * cosT);
      zRow.push(xsec.xyz[2] + xsec.b * r * sinT);
    }
    xGrid.push(xRow);
    yGrid.push(yRow);
    zGrid.push(zRow);
  }

  return {
    x: xGrid,
    y: yGrid,
    z: zGrid,
    type: "surface",
    colorscale: [[0, color], [1, color]],
    showscale: false,
    opacity,
    name,
  };
}

/** Plotly 3D preview of fuselage from xsecs — lazy loaded */
function FuselagePreview3D({ xsecs, selectedXsec }: Readonly<{ xsecs: XSec[]; selectedXsec: number | null }>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotlyRef = useRef<{ restyle: (el: HTMLDivElement, update: Record<string, unknown>, indices: number[]) => void } | null>(null);
  const cameraRef = useRef<Record<string, unknown> | null>(null);

  // Initial plot + full rebuild when xsecs change
  useEffect(() => {
    const node = containerRef.current;
    if (!node || xsecs.length < 2) return;
    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;
      plotlyRef.current = Plotly.default;

      const surfaceTrace = buildFuselageSurface(xsecs, "#FF8400", 0.7, "Reconstructed", 32);

      const xsecTraces = xsecs.map((xsec, idx) => {
        const pts = 48;
        const x: number[] = [];
        const y: number[] = [];
        const z: number[] = [];
        for (let j = 0; j <= pts; j++) {
          const t = (j / pts) * 2 * Math.PI;
          const cosT = Math.cos(t);
          const sinT = Math.sin(t);
          const r = Math.pow(
            Math.pow(Math.abs(cosT), xsec.n) + Math.pow(Math.abs(sinT), xsec.n),
            -1 / xsec.n,
          );
          x.push(xsec.xyz[0]);
          y.push(xsec.xyz[1] + xsec.a * r * cosT);
          z.push(xsec.xyz[2] + xsec.b * r * sinT);
        }
        return {
          x, y, z,
          type: "scatter3d",
          mode: "lines",
          line: { color: "#B8B9B6", width: 1.5 },
          showlegend: false,
          hoverinfo: "text",
          text: `Section ${idx}`,
        };
      });

      const layout = {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#B8B9B6" },
        margin: { l: 0, r: 0, t: 0, b: 0 },
        scene: {
          bgcolor: "#17171A",
          aspectmode: "data" as const,
          xaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A" },
          yaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A" },
          zaxis: { showgrid: true, gridcolor: "#2E2E2E", zerolinecolor: "#3A3A3A" },
        },
      };

      // Restore saved camera position (preserved across re-renders)
      if (cameraRef.current) {
        layout.scene = { ...layout.scene, camera: cameraRef.current } as typeof layout.scene;
      }

      await Plotly.default.react(
        node,
        [surfaceTrace as Record<string, unknown>, ...xsecTraces as Record<string, unknown>[]],
        layout,
        {
          responsive: true,
          displayModeBar: true,
          modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
        },
      );

      // Apply selection highlight immediately after render
      if (selectedXsec !== null && xsecs.length > 0) {
        const traceIndices = xsecs.map((_, i) => i + 1);
        const colors = xsecs.map((_, idx) => selectedXsec === idx ? "#E5484D" : "#B8B9B6");
        const widths = xsecs.map((_, idx) => selectedXsec === idx ? 5 : 1.5);
        (Plotly.default as unknown as { restyle: (el: HTMLDivElement, update: Record<string, unknown>, indices: number[]) => void })
          .restyle(node, { "line.color": colors, "line.width": widths }, traceIndices);
      }

      // Listen for camera changes and save them
      (node as unknown as { on?: (event: string, cb: (update: Record<string, unknown>) => void) => void })
        .on?.("plotly_relayout", (update: Record<string, unknown>) => {
          if (update?.["scene.camera"]) {
            cameraRef.current = update["scene.camera"] as Record<string, unknown>;
          }
        });
    })();

    return () => {
      disposed = true;
      if (node) {
        import("plotly.js-gl3d-dist-min")
          .then((P) => P.default.purge(node))
          .catch(() => { /* cleanup — safe to ignore */ });
      }
    };
  }, [xsecs]);

  // Selection highlight — single batch restyle, preserves camera
  useEffect(() => {
    if (!containerRef.current || !plotlyRef.current || xsecs.length < 2) return;
    const Plotly = plotlyRef.current;

    // Batch: update all cross-section traces (indices 1..N) in one call
    const traceIndices = xsecs.map((_, i) => i + 1); // skip index 0 (surface)
    const colors = xsecs.map((_, idx) => selectedXsec === idx ? "#E5484D" : "#B8B9B6");
    const widths = xsecs.map((_, idx) => selectedXsec === idx ? 5 : 1.5);

    Plotly.restyle(containerRef.current, {
      "line.color": colors,
      "line.width": widths,
    }, traceIndices);
  }, [selectedXsec, xsecs.length]);

  return <div ref={containerRef} className="h-full w-full" />;
}

/** Generate SVG path for a superellipse |x/a|^n + |y/b|^n = 1 */
function superellipsePath(a: number, b: number, n: number, samples: number = 64): string {
  const points: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const t = (i / samples) * 2 * Math.PI;
    const cosT = Math.cos(t);
    const sinT = Math.sin(t);
    const r = Math.pow(
      Math.pow(Math.abs(cosT), n) + Math.pow(Math.abs(sinT), n),
      -1 / n,
    );
    const px = a * r * cosT;
    const py = b * r * sinT;
    points.push(`${i === 0 ? "M" : "L"}${px.toFixed(3)},${py.toFixed(3)}`);
  }
  return points.join(" ") + "Z";
}

interface XSec {
  xyz: number[];
  a: number;
  b: number;
  n: number;
}

interface ImportFuselageDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string | null;
  onSaved?: () => void;
  /** Pre-load with existing fuselage data — skips upload phase, goes straight to preview */
  initialXsecs?: XSec[];
  initialName?: string;
  initialSelectedIndex?: number;
}

/** Extract fidelity metrics from the slicing response */
function extractFidelity(
  data: Record<string, unknown>,
): { volume_ratio: number; area_ratio: number } | null {
  const f = data.fidelity as { volume_ratio?: number; area_ratio?: number } | undefined;
  if (f && (f.volume_ratio || f.area_ratio)) {
    return { volume_ratio: f.volume_ratio ?? 0, area_ratio: f.area_ratio ?? 0 };
  }
  const orig = data.original_properties as { volume_m3?: number; surface_area_m2?: number } | undefined;
  const recon = data.reconstructed_properties as { volume_m3?: number; surface_area_m2?: number } | undefined;
  if (orig && recon) {
    const ov = orig.volume_m3 ?? 0;
    const rv = recon.volume_m3 ?? 0;
    const oa = orig.surface_area_m2 ?? 0;
    const ra = recon.surface_area_m2 ?? 0;
    return {
      volume_ratio: ov > 0 ? rv / ov : 0,
      area_ratio: oa > 0 ? ra / oa : 0,
    };
  }
  return null;
}

/** Cross-section SVG preview with slider and add/delete controls */
function CrossSectionSvg({
  xsecs,
  selectedXsec,
  setSelectedXsec,
  setXsecs,
}: Readonly<{
  xsecs: XSec[];
  selectedXsec: number | null;
  setSelectedXsec: (idx: number | null) => void;
  setXsecs: React.Dispatch<React.SetStateAction<XSec[]>>;
}>) {
  const idx = selectedXsec ?? 0;
  const xsec = xsecs[idx];
  if (!xsec) return null;

  const maxDim = Math.max(xsec.a, xsec.b, 0.001);
  const viewSize = 1.2 * maxDim;

  const handleInsert = () => {
    const next = xsecs[Math.min(idx + 1, xsecs.length - 1)];
    const newXsec: XSec = {
      xyz: xsec.xyz.map((v, j) => (v + next.xyz[j]) / 2),
      a: (xsec.a + next.a) / 2,
      b: (xsec.b + next.b) / 2,
      n: (xsec.n + next.n) / 2,
    };
    setXsecs((prev) => [
      ...prev.slice(0, idx + 1),
      newXsec,
      ...prev.slice(idx + 1),
    ]);
    setSelectedXsec(idx + 1);
  };

  const handleDelete = () => {
    if (xsecs.length <= 2) return;
    setXsecs((prev) => prev.filter((_, i) => i !== idx));
    setSelectedXsec(Math.min(idx, xsecs.length - 2));
  };

  return (
    <>
      <svg
        viewBox={`${-viewSize} ${-viewSize} ${viewSize * 2} ${viewSize * 2}`}
        className="flex-1 w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Grid */}
        <line x1={-viewSize} y1={0} x2={viewSize} y2={0} stroke="#2E2E2E" strokeWidth={viewSize * 0.005} />
        <line x1={0} y1={-viewSize} x2={0} y2={viewSize} stroke="#2E2E2E" strokeWidth={viewSize * 0.005} />
        {/* Superellipse */}
        <path
          d={superellipsePath(xsec.a, xsec.b, xsec.n)}
          fill="rgba(255,132,0,0.15)"
          stroke="#FF8400"
          strokeWidth={viewSize * 0.01}
        />
        {/* Dimension labels */}
        <text x={xsec.a * 0.5} y={-viewSize * 0.85} fill="#B8B9B6" fontSize={viewSize * 0.08} textAnchor="middle">
          a={xsec.a.toFixed(4)}
        </text>
        <text x={viewSize * 0.85} y={xsec.b * 0.5} fill="#B8B9B6" fontSize={viewSize * 0.08} textAnchor="end">
          b={xsec.b.toFixed(4)}
        </text>
      </svg>
      {/* Slider + nav + add/delete */}
      <div className="flex w-full items-center gap-1.5">
        <button
          onClick={() => setSelectedXsec(Math.max(0, idx - 1))}
          disabled={idx <= 0}
          className="flex size-6 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground disabled:opacity-30"
        >{"<"}</button>
        <input
          type="range"
          min={0}
          max={xsecs.length - 1}
          value={idx}
          onChange={(e) => setSelectedXsec(Number.parseInt(e.target.value))}
          className="flex-1 accent-primary"
        />
        <button
          onClick={() => setSelectedXsec(Math.min(xsecs.length - 1, idx + 1))}
          disabled={idx >= xsecs.length - 1}
          className="flex size-6 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground disabled:opacity-30"
        >{">"}</button>
        <span className="shrink-0 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground w-12 text-center">
          {idx + 1}/{xsecs.length}
        </span>
        <button
          onClick={handleInsert}
          className="flex size-6 shrink-0 items-center justify-center rounded-full border border-border text-success hover:bg-success/20"
          title="Insert section after current (interpolated)"
        >
          <Plus size={12} />
        </button>
        <button
          onClick={handleDelete}
          disabled={xsecs.length <= 2}
          className="flex size-6 shrink-0 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20 disabled:opacity-30"
          title="Delete current section"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </>
  );
}

/** Parameter editor for the selected cross-section */
function XSecParameterEditor({
  xsecs,
  selectedXsec,
  setXsecs,
}: Readonly<{
  xsecs: XSec[];
  selectedXsec: number | null;
  setXsecs: React.Dispatch<React.SetStateAction<XSec[]>>;
}>) {
  const idx = selectedXsec ?? 0;
  const xsec = xsecs[idx];
  if (!xsec) return null;

  const update = (field: keyof XSec, value: number, subIdx?: number) => {
    setXsecs((prev) => prev.map((xs, i) => {
      if (i !== idx) return xs;
      if (field === "xyz" && subIdx !== undefined) {
        const newXyz = [...xs.xyz];
        newXyz[subIdx] = value;
        return { ...xs, xyz: newXyz };
      }
      return { ...xs, [field]: value };
    }));
  };

  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        {(["x", "y", "z"] as const).map((ax, i) => (
          <div key={ax} className="flex flex-col gap-0.5">
            <label htmlFor={`xsec-xyz-${ax}`} className="text-[9px] text-muted-foreground">xyz[{ax}]</label>
            <input id={`xsec-xyz-${ax}`} type="number" step="0.001" value={xsec.xyz[i]}
              onChange={(e) => update("xyz", Number.parseFloat(e.target.value) || 0, i)}
              className="w-full rounded-xl border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col gap-0.5">
          <label htmlFor="xsec-a" className="text-[9px] text-muted-foreground">a (width/2)</label>
          <input id="xsec-a" type="number" step="0.001" value={xsec.a}
            onChange={(e) => update("a", Number.parseFloat(e.target.value) || 0.001)}
            className="w-full rounded-xl border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground" />
        </div>
        <div className="flex flex-col gap-0.5">
          <label htmlFor="xsec-b" className="text-[9px] text-muted-foreground">b (height/2)</label>
          <input id="xsec-b" type="number" step="0.001" value={xsec.b}
            onChange={(e) => update("b", Number.parseFloat(e.target.value) || 0.001)}
            className="w-full rounded-xl border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground" />
        </div>
      </div>
      <div className="flex flex-col gap-0.5">
        <label htmlFor="xsec-n" className="text-[9px] text-muted-foreground">n (exponent)</label>
        <input id="xsec-n" type="number" step="0.1" value={xsec.n}
          onChange={(e) => update("n", Math.max(0.5, Math.min(10, Number.parseFloat(e.target.value) || 2)))}
          className="w-full rounded-xl border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground" />
      </div>
    </>
  );
}

// Dummy data for the mock
const INITIAL_XSECS: XSec[] = Array.from({ length: 50 }, (_, i) => ({
  xyz: [i * 0.008, 0, 0],
  a: 0.005 + 0.04 * Math.sin((i / 49) * Math.PI),
  b: 0.005 + 0.03 * Math.sin((i / 49) * Math.PI),
  n: 2 + 0.5 * Math.sin((i / 49) * Math.PI),
}));

/** Transform raw sliced xsecs by applying scale and optional X-flip. */
function transformSlicedXsecs(
  rawXsecs: Array<{ xyz: number[]; a: number; b: number; n: number }>,
  scaleFactor: number,
  flipX: boolean,
): XSec[] {
  const xFlip = flipX ? -1 : 1;
  return rawXsecs.map((xs) => ({
    xyz: xs.xyz.map((v: number, idx: number) => v * scaleFactor * (idx === 0 ? xFlip : 1)),
    a: xs.a * scaleFactor,
    b: xs.b * scaleFactor,
    n: xs.n,
  }));
}

/** Save a fuselage via PUT, falling back to POST on 409 conflict. */
async function saveFuselage(
  aeroplaneId: string,
  fuselageName: string,
  xsecs: XSec[],
): Promise<void> {
  const body = JSON.stringify({
    name: fuselageName,
    x_secs: xsecs.map((xs) => ({ xyz: xs.xyz, a: xs.a, b: xs.b, n: xs.n })),
  });

  let res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}`,
    { method: "PUT", headers: { "Content-Type": "application/json" }, body },
  );
  if (res.status === 409) {
    res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body },
    );
  }
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Save failed: ${res.status} ${detail}`);
  }
}

/** Perform the slicing API call and return parsed xsecs + metadata. */
async function performSlicing(
  file: File,
  slices: number,
  axis: string,
  fuselageName: string,
  scaleFactor: number,
  flipX: boolean,
): Promise<{ xsecs: XSec[]; fidelity: { volume_ratio: number; area_ratio: number } | null; name: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("number_of_slices", String(slices));
  formData.append("points_per_slice", "30");
  formData.append("slice_axis", axis);
  formData.append("fuselage_name", fuselageName);

  const res = await fetch(`${API_BASE}/fuselages/slice`, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Slicing failed: ${res.status} ${body}`);
  }
  const data = await res.json();
  const newXsecs = transformSlicedXsecs(data.fuselage?.x_secs ?? [], scaleFactor, flipX);
  return {
    xsecs: newXsecs.length > 0 ? newXsecs : INITIAL_XSECS,
    fidelity: extractFidelity(data),
    name: data.fuselage?.name ?? fuselageName,
  };
}

/** Build default xsecs for the "create empty" flow. */
function buildDefaultXsecs(scaleFactor: number, flipX: boolean): XSec[] {
  const raw: XSec[] = [
    { xyz: [0, 0, 0], a: 0.01, b: 0.01, n: 2 },
    { xyz: [0.1, 0, 0], a: 0.05, b: 0.04, n: 2 },
    { xyz: [0.3, 0, 0], a: 0.05, b: 0.04, n: 2 },
    { xyz: [0.4, 0, 0], a: 0.01, b: 0.01, n: 2 },
  ];
  return raw.map(xs => ({
    ...xs,
    xyz: xs.xyz.map((v, idx) => v * scaleFactor * (idx === 0 && flipX ? -1 : 1)),
    a: xs.a * scaleFactor,
    b: xs.b * scaleFactor,
  }));
}

type Phase = "upload" | "processing" | "preview";

// ── Upload phase renderer (extracted for cognitive complexity) ──

interface UploadPhaseProps {
  fileName: string | null;
  handleFileSelect: (f: File) => void;
  handleCreateEmpty: () => void;
  error: string | null;
  fuselageName: string;
  setFuselageName: (v: string) => void;
  scaleInput: string;
  setScaleInput: (v: string) => void;
  scaleFactor: number;
  setScaleFactor: (v: number) => void;
  flipX: boolean;
  setFlipX: (fn: (v: boolean) => boolean) => void;
  slicesInput: string;
  setSlicesInput: (v: string) => void;
  slices: number;
  setSlices: (v: number) => void;
  axis: string;
  setAxis: (v: string) => void;
  handleStartSlicing: () => void;
}

function renderUploadPhase(p: UploadPhaseProps) {
  return (
    <div className="flex flex-col gap-5">
      {/* Two options: import or create */}
      <div className="flex gap-4">
        {/* Option 1: Import from STEP */}
        <label className={`flex flex-1 h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed transition-colors ${
          p.fileName ? "border-primary bg-primary/10" : "border-border bg-card-muted hover:border-primary hover:bg-card-muted/80"
        }`}>
          <Upload size={28} className={p.fileName ? "text-primary" : "text-muted-foreground"} />
          <span className={`text-[13px] ${p.fileName ? "text-foreground" : "text-muted-foreground"}`}>
            {p.fileName ?? "Import from STEP file"}
          </span>
          <span className="text-[10px] text-subtle-foreground">
            {p.fileName ? "Click to change file" : ".step, .stp"}
          </span>
          <input
            type="file"
            accept=".step,.stp"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) p.handleFileSelect(f);
            }}
          />
        </label>

        {/* Option 2: Create empty */}
        <button
          onClick={p.handleCreateEmpty}
          className="flex flex-1 h-40 flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border bg-card-muted hover:border-primary hover:bg-card-muted/80 transition-colors"
        >
          <Plus size={28} className="text-muted-foreground" />
          <span className="text-[13px] text-muted-foreground">
            Create manually
          </span>
          <span className="text-[10px] text-subtle-foreground">
            Start with 4 default sections
          </span>
        </button>
      </div>
      {p.error && (
        <div className="rounded-xl border border-destructive bg-destructive/10 p-3 text-[12px] text-destructive">
          {p.error}
        </div>
      )}

      {/* Parameters */}
      <div className="flex gap-4">
        <div className="flex flex-1 flex-col gap-1">
          <label htmlFor="fuselage-name" className="text-[11px] text-muted-foreground">
            Fuselage Name
          </label>
          <input
            id="fuselage-name"
            type="text"
            value={p.fuselageName}
            onChange={(e) => p.setFuselageName(e.target.value)}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="fuselage-scale-factor" className="text-[11px] text-muted-foreground">Scale Factor</label>
          <div className="flex items-center gap-2">
            <input
              id="fuselage-scale-factor"
              type="text"
              inputMode="decimal"
              value={p.scaleInput}
              onChange={(e) => {
                p.setScaleInput(e.target.value);
                const v = Number.parseFloat(e.target.value);
                if (!Number.isNaN(v) && v > 0) p.setScaleFactor(v);
              }}
              onBlur={() => p.setScaleInput(String(p.scaleFactor))}
              className="w-24 rounded-xl border border-border bg-input px-3 py-2 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground"
            />
            <button
              onClick={() => { p.setScaleFactor(0.001); p.setScaleInput("0.001"); }}
              className={`rounded-full px-2 py-1 text-[10px] ${p.scaleFactor === 0.001 ? "bg-primary text-primary-foreground" : "bg-card-muted text-muted-foreground hover:text-foreground"}`}
            >
              mm→m
            </button>
            <button
              onClick={() => { p.setScaleFactor(0.01); p.setScaleInput("0.01"); }}
              className={`rounded-full px-2 py-1 text-[10px] ${p.scaleFactor === 0.01 ? "bg-primary text-primary-foreground" : "bg-card-muted text-muted-foreground hover:text-foreground"}`}
            >
              cm→m
            </button>
            <button
              onClick={() => { p.setScaleFactor(1); p.setScaleInput("1"); }}
              className={`rounded-full px-2 py-1 text-[10px] ${p.scaleFactor === 1 ? "bg-primary text-primary-foreground" : "bg-card-muted text-muted-foreground hover:text-foreground"}`}
            >
              1:1
            </button>
            <span className="mx-1 text-[9px] text-subtle-foreground">|</span>
            <button
              onClick={() => p.setFlipX((v) => !v)}
              className={`rounded-full px-2 py-1 text-[10px] ${p.flipX ? "bg-primary text-primary-foreground" : "bg-card-muted text-muted-foreground hover:text-foreground"}`}
              title="Flip X axis (reverse nose direction)"
            >
              Flip X
            </button>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="fuselage-slices" className="text-[11px] text-muted-foreground">
            Slices
          </label>
          <input
            id="fuselage-slices"
            type="text"
            inputMode="numeric"
            value={p.slicesInput}
            onChange={(e) => {
              p.setSlicesInput(e.target.value);
              const v = Number.parseInt(e.target.value, 10);
              if (!Number.isNaN(v) && v >= 2 && v <= 500) p.setSlices(v);
            }}
            onBlur={() => p.setSlicesInput(String(p.slices))}
            className="w-20 rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="fuselage-slice-axis" className="text-[11px] text-muted-foreground">
            Slice Axis
          </label>
          <select
            id="fuselage-slice-axis"
            value={p.axis}
            onChange={(e) => p.setAxis(e.target.value)}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
          >
            <option value="auto">auto</option>
            <option value="x">x</option>
            <option value="y">y</option>
            <option value="z">z</option>
          </select>
        </div>
      </div>

      {/* Start Slicing button — only shown when file is selected */}
      {p.fileName && (
        <button
          onClick={p.handleStartSlicing}
          className="flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-2.5 text-[13px] text-primary-foreground hover:opacity-90 self-end"
        >
          <Play size={14} />
          Start Slicing
        </button>
      )}
    </div>
  );
}

// ── Preview phase renderer (extracted for cognitive complexity) ──

interface PreviewPhaseProps {
  xsecs: XSec[];
  selectedXsec: number | null;
  setSelectedXsec: (v: number | null) => void;
  setXsecs: (v: XSec[]) => void;
  viewerMaximized: boolean;
  setViewerMaximized: (fn: (v: boolean) => boolean) => void;
  xsecsMaximized: boolean;
  setXsecsMaximized: (fn: (v: boolean) => boolean) => void;
  fidelity: { volume_ratio: number; area_ratio: number } | null;
  fuselageName: string;
  setFuselageName: (v: string) => void;
}

function renderPreviewPhase(p: PreviewPhaseProps) {
  return (
    <div className="flex flex-1 flex-col gap-4 min-h-0">
      {/* Combined 3D viewer — hidden when cross-sections maximized */}
      {!p.xsecsMaximized && <div className="relative">
        <button
          onClick={() => p.setViewerMaximized((m) => !m)}
          className="absolute right-2 top-2 z-10 flex size-8 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title={p.viewerMaximized ? "Restore size" : "Maximize viewer"}
        >
          {p.viewerMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
        <div className="min-h-[150px] max-h-[35vh] rounded-xl border border-border bg-[#17171A] overflow-hidden">
          <FuselagePreview3D xsecs={p.xsecs} selectedXsec={p.selectedXsec} />
        </div>
      </div>}

      {/* Fidelity metrics — hidden when either view is maximized */}
      {!p.viewerMaximized && !p.xsecsMaximized && (
      <div className="flex gap-4">
        <div className="flex flex-1 items-center gap-3 rounded-xl border border-border bg-card-muted px-4 py-2">
          <span className="text-[12px] text-muted-foreground">Volume Fidelity</span>
          <span className="flex-1" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {((p.fidelity?.volume_ratio ?? 0) * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex flex-1 items-center gap-3 rounded-xl border border-border bg-card-muted px-4 py-2">
          <span className="text-[12px] text-muted-foreground">Area Fidelity</span>
          <span className="flex-1" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {((p.fidelity?.area_ratio ?? 0) * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      )}

      {/* Cross-section viewer — single section with slider + params */}
      {!p.viewerMaximized && (
      <div className={`relative flex rounded-xl border border-border bg-card-muted ${p.xsecsMaximized ? "flex-1 min-h-0" : "h-[220px] shrink-0"}`}>
        <button
          onClick={() => { p.setXsecsMaximized((m) => !m); }}
          className="absolute right-2 top-2 z-10 flex size-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title={p.xsecsMaximized ? "Restore size" : "Maximize cross-sections"}
        >
          {p.xsecsMaximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
        </button>

        {/* Left: single SVG cross-section + slider */}
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-4">
          <CrossSectionSvg
            xsecs={p.xsecs}
            selectedXsec={p.selectedXsec}
            setSelectedXsec={p.setSelectedXsec}
            setXsecs={p.setXsecs}
          />
        </div>

        {/* Right: parameter editor */}
        <div className="flex w-[280px] shrink-0 flex-col gap-2 border-l border-border p-4 overflow-y-auto">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary">
            Section {p.selectedXsec ?? 0} Parameters
          </span>
          <XSecParameterEditor
            xsecs={p.xsecs}
            selectedXsec={p.selectedXsec}
            setXsecs={p.setXsecs}
          />
        </div>
      </div>
      )}

      {/* Fuselage name (editable) — hidden when either view maximized */}
      {!p.viewerMaximized && !p.xsecsMaximized && (
      <div className="flex items-center gap-3">
        <label htmlFor="fuselage-save-as" className="text-[11px] text-muted-foreground">Save as:</label>
        <input
          id="fuselage-save-as"
          type="text"
          value={p.fuselageName}
          onChange={(e) => p.setFuselageName(e.target.value)}
          className="flex-1 rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
        />
      </div>
      )}
    </div>
  );
}

export function ImportFuselageDialog({
  open,
  onClose,
  aeroplaneId,
  onSaved,
  initialXsecs,
  initialName,
  initialSelectedIndex,
}: Readonly<ImportFuselageDialogProps>) {
  const editMode = !!initialXsecs;
  const [phase, setPhase] = useState<Phase>(editMode ? "preview" : "upload");
  const [fileName, setFileName] = useState<string | null>(null);
  const [slices, setSlices] = useState(50);
  const [slicesInput, setSlicesInput] = useState("50");
  const [axis, setAxis] = useState("auto");
  const [scaleFactor, setScaleFactor] = useState(1);
  const [scaleInput, setScaleInput] = useState("1");
  const [flipX, setFlipX] = useState(false);
  const [fuselageName, setFuselageName] = useState(initialName ?? "Imported Fuselage");
  const [viewerMaximized, setViewerMaximized] = useState(false);
  const [xsecsMaximized, setXsecsMaximized] = useState(false);
  const [xsecs, setXsecs] = useState<XSec[]>(initialXsecs ?? INITIAL_XSECS);
  const [selectedXsec, setSelectedXsec] = useState<number | null>(initialSelectedIndex ?? (editMode ? 0 : null));
  // zoomScale state removed — was unused dead code (SonarQube S1854)
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fidelity, setFidelity] = useState<{ volume_ratio: number; area_ratio: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const { dialogRef, handleClose: dialogHandleClose } = useDialog(open, () => { handleReset(); onClose(); });

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setFileName(selectedFile.name);
    setError(null);
    // Stay in upload phase — user clicks "Start Slicing" when ready
  };

  const handleStartSlicing = async () => {
    if (!file) return;
    setPhase("processing");
    setError(null);
    try {
      const result = await performSlicing(file, slices, axis, fuselageName, scaleFactor, flipX);
      setXsecs(result.xsecs);
      setFidelity(result.fidelity);
      setFuselageName(result.name);
      setSelectedXsec(0);
      setPhase("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("upload");
    }
  };

  const handleAccept = async () => {
    if (!aeroplaneId) { setError("No aeroplane selected"); return; }
    setSaving(true);
    setError(null);
    try {
      await saveFuselage(aeroplaneId, fuselageName, xsecs);
      onSaved?.();
      handleReset();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleCreateEmpty = () => {
    setXsecs(buildDefaultXsecs(scaleFactor, flipX));
    setFileName(null);
    setFidelity(null);
    setSelectedXsec(0);
    setPhase("preview");
  };

  const handleReset = () => {
    setPhase(editMode ? "preview" : "upload");
    setFileName(null);
    setSlices(50);
    setSlicesInput("50");
    setAxis("auto");
    setScaleFactor(1);
    setScaleInput("1");
    setFlipX(false);
    setFuselageName(initialName ?? "Imported Fuselage");
    setXsecs(initialXsecs ?? INITIAL_XSECS);
    setSelectedXsec(initialSelectedIndex ?? (editMode ? 0 : null));
    setZoomScale(null);
    setXsecsMaximized(false);
    setViewerMaximized(false);
    setFile(null);
    setError(null);
    setFidelity(null);
    setSaving(false);
  };

  return (
    <dialog
      ref={dialogRef}
      className="z-50 backdrop:bg-black/60"
      onClose={dialogHandleClose}
      aria-label="New Fuselage"
    >
      <div
        className={`flex flex-col rounded-2xl border border-border bg-card shadow-2xl transition-all ${
          viewerMaximized || xsecsMaximized
            ? "fixed inset-4 z-50 w-auto"
            : "w-[900px] h-[80vh]"
        }`}
      >
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border px-6 py-4">
          <Upload size={20} className="text-primary" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            New Fuselage
          </span>
          <span className="flex-1" />
          <button
            onClick={() => { handleReset(); onClose(); }}
            className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 flex flex-col overflow-hidden px-6 py-5">
          {phase === "upload" && renderUploadPhase({
            fileName, handleFileSelect, handleCreateEmpty, error,
            fuselageName, setFuselageName,
            scaleInput, setScaleInput, scaleFactor, setScaleFactor,
            flipX, setFlipX,
            slicesInput, setSlicesInput, slices, setSlices,
            axis, setAxis, handleStartSlicing,
          })}

          {phase === "processing" && (
            <div className="flex h-60 flex-col items-center justify-center gap-4">
              <Loader2 size={40} className="animate-spin text-primary" />
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
                Slicing {fileName}...
              </span>
              <span className="text-[12px] text-subtle-foreground">
                Fitting symmetric superellipses to {slices} cross-sections
              </span>
            </div>
          )}

          {phase === "preview" && renderPreviewPhase({
            xsecs, selectedXsec, setSelectedXsec, setXsecs,
            viewerMaximized, setViewerMaximized,
            xsecsMaximized, setXsecsMaximized,
            fidelity, fuselageName, setFuselageName,
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 border-t border-border px-6 py-4">
          {phase === "preview" && (
            <button
              onClick={handleReset}
              className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Try Another File
            </button>
          )}
          <span className="flex-1" />
          <button
            onClick={() => { handleReset(); onClose(); }}
            className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
          {phase === "preview" && (
            <button
              onClick={handleAccept}
              disabled={saving || !aeroplaneId}
              className="flex items-center gap-2 rounded-full bg-primary px-5 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              {saving ? "Saving\u2026" : "Accept & Save"}
            </button>
          )}
        </div>
      </div>
    </dialog>
  );
}
