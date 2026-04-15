"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { Upload, X, Check, Loader2, AlertTriangle, Maximize2, Minimize2 } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";

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
function FuselagePreview3D({ xsecs }: { xsecs: XSec[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || xsecs.length < 2) return;
    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed || !containerRef.current) return;

      const trace = buildFuselageSurface(xsecs, "#FF8400", 0.7, "Reconstructed", 32);

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

      Plotly.default.react(containerRef.current, [trace as any], layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"] as any[],
      });
    })();

    return () => {
      disposed = true;
      if (containerRef.current) {
        import("plotly.js-gl3d-dist-min")
          .then((P) => P.default.purge(containerRef.current!))
          .catch(() => {});
      }
    };
  }, [xsecs]);

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

interface ImportFuselageDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string | null;
  onSaved?: () => void;
}

interface XSec {
  xyz: number[];
  a: number;
  b: number;
  n: number;
}

// Dummy data for the mock
const INITIAL_XSECS: XSec[] = Array.from({ length: 50 }, (_, i) => ({
  xyz: [i * 0.008, 0, 0],
  a: 0.005 + 0.04 * Math.sin((i / 49) * Math.PI),
  b: 0.005 + 0.03 * Math.sin((i / 49) * Math.PI),
  n: 2.0 + 0.5 * Math.sin((i / 49) * Math.PI),
}));

type Phase = "upload" | "processing" | "preview";

export function ImportFuselageDialog({
  open,
  onClose,
  aeroplaneId,
  onSaved,
}: ImportFuselageDialogProps) {
  const [phase, setPhase] = useState<Phase>("upload");
  const [fileName, setFileName] = useState<string | null>(null);
  const [slices, setSlices] = useState(50);
  const [axis, setAxis] = useState("auto");
  const [fuselageName, setFuselageName] = useState("Imported Fuselage");
  const [viewerMaximized, setViewerMaximized] = useState(false);
  const [xsecsMaximized, setXsecsMaximized] = useState(false);
  const [xsecs, setXsecs] = useState<XSec[]>(INITIAL_XSECS);
  const [selectedXsec, setSelectedXsec] = useState<number | null>(null);
  const [zoomScale, setZoomScale] = useState<number | null>(null); // null = auto-fit selected
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fidelity, setFidelity] = useState<{ volume_ratio: number; area_ratio: number } | null>(null);
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setFileName(selectedFile.name);
    setError(null);
    setPhase("processing");

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("number_of_slices", String(slices));
    formData.append("points_per_slice", "30");
    formData.append("slice_axis", axis);
    formData.append("fuselage_name", fuselageName);

    fetch(`${API_BASE}/fuselages/slice`, { method: "POST", body: formData })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Slicing failed: ${res.status} ${body}`);
        }
        return res.json();
      })
      .then((data) => {
        const newXsecs: XSec[] = (data.fuselage?.x_secs ?? []).map((xs: any) => ({
          xyz: xs.xyz,
          a: xs.a,
          b: xs.b,
          n: xs.n,
        }));
        setXsecs(newXsecs.length > 0 ? newXsecs : INITIAL_XSECS);
        setFidelity(data.fidelity ?? null);
        setFuselageName(data.fuselage?.name ?? fuselageName);
        setPhase("preview");
      })
      .catch((err) => {
        setError(err.message);
        setPhase("upload");
      });
  };

  const handleAccept = async () => {
    if (!aeroplaneId) { setError("No aeroplane selected"); return; }
    setSaving(true);
    setError(null);
    try {
      // First create the fuselage if it doesn't exist
      await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: fuselageName,
            x_secs: xsecs.map((xs) => ({ xyz: xs.xyz, a: xs.a, b: xs.b, n: xs.n })),
          }),
        },
      );
      onSaved?.();
      handleReset();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setPhase("upload");
    setFileName(null);
    setSlices(50);
    setAxis("auto");
    setFuselageName("Imported Fuselage");
    setXsecs(INITIAL_XSECS);
    setSelectedXsec(null);
    setZoomScale(null);
    setXsecsMaximized(false);
    setViewerMaximized(false);
    setFile(null);
    setError(null);
    setFidelity(null);
    setSaving(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className={`flex flex-col rounded-2xl border border-border bg-card shadow-2xl transition-all ${
          viewerMaximized || xsecsMaximized
            ? "fixed inset-4 z-50 max-h-none w-auto"
            : "w-[900px] max-h-[80vh]"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border px-6 py-4">
          <Upload size={20} className="text-primary" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            Import Fuselage from STEP
          </span>
          <span className="flex-1" />
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className={`flex-1 px-6 py-5 ${viewerMaximized || xsecsMaximized ? "flex flex-col overflow-hidden" : "overflow-y-auto"}`}>
          {phase === "upload" && (
            <div className="flex flex-col gap-5">
              {/* File drop zone */}
              <label className="flex h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border bg-card-muted hover:border-primary hover:bg-card-muted/80 transition-colors">
                <Upload size={32} className="text-muted-foreground" />
                <span className="text-[14px] text-muted-foreground">
                  Click to select a STEP file
                </span>
                <span className="text-[11px] text-subtle-foreground">
                  Supported: .step, .stp
                </span>
                <input
                  type="file"
                  accept=".step,.stp"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFileSelect(f);
                  }}
                />
              </label>
              {error && (
                <div className="rounded-xl border border-destructive bg-destructive/10 p-3 text-[12px] text-destructive">
                  {error}
                </div>
              )}

              {/* Parameters */}
              <div className="flex gap-4">
                <div className="flex flex-1 flex-col gap-1">
                  <label className="text-[11px] text-muted-foreground">
                    Fuselage Name
                  </label>
                  <input
                    type="text"
                    value={fuselageName}
                    onChange={(e) => setFuselageName(e.target.value)}
                    className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-muted-foreground">
                    Slices
                  </label>
                  <input
                    type="number"
                    value={slices}
                    onChange={(e) => setSlices(parseInt(e.target.value) || 50)}
                    className="w-20 rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-muted-foreground">
                    Slice Axis
                  </label>
                  <select
                    value={axis}
                    onChange={(e) => setAxis(e.target.value)}
                    className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                  >
                    <option value="auto">auto</option>
                    <option value="x">x</option>
                    <option value="y">y</option>
                    <option value="z">z</option>
                  </select>
                </div>
              </div>
            </div>
          )}

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

          {phase === "preview" && (
            <div className={`flex flex-col gap-5 ${viewerMaximized || xsecsMaximized ? "flex-1 min-h-0" : ""}`}>
              {/* Combined 3D viewer — hidden when cross-sections maximized */}
              {!xsecsMaximized && <div className="relative">
                <button
                  onClick={() => setViewerMaximized((m) => !m)}
                  className="absolute right-2 top-2 z-10 flex size-8 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                  title={viewerMaximized ? "Restore size" : "Maximize viewer"}
                >
                  {viewerMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>
                <div className={`rounded-xl border border-border bg-[#17171A] overflow-hidden ${viewerMaximized ? "flex-1" : "h-64"}`}>
                  <FuselagePreview3D xsecs={xsecs} />
                </div>
              </div>}

              {/* Fidelity metrics — hidden when either view is maximized */}
              {!viewerMaximized && !xsecsMaximized && (
              <div className="flex gap-4">
                <div className="flex flex-1 items-center gap-3 rounded-xl border border-border bg-card-muted p-4">
                  <span className="text-[12px] text-muted-foreground">Volume Fidelity</span>
                  <span className="flex-1" />
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                    {((fidelity?.volume_ratio ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex flex-1 items-center gap-3 rounded-xl border border-border bg-card-muted p-4">
                  <span className="text-[12px] text-muted-foreground">Area Fidelity</span>
                  <span className="flex-1" />
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                    {((fidelity?.area_ratio ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              )}

              {/* Cross-section summary — always visible (has own maximize) */}
              {!viewerMaximized && (
              <div className={`relative flex flex-col rounded-xl border border-border bg-card-muted p-4 ${xsecsMaximized ? "flex-1 min-h-0" : ""}`}>
                <button
                  onClick={() => { setXsecsMaximized((m) => !m); if (xsecsMaximized) setSelectedXsec(null); }}
                  className="absolute right-2 top-2 z-10 flex size-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                  title={xsecsMaximized ? "Restore size" : "Maximize cross-sections"}
                >
                  {xsecsMaximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
                </button>
                <div className="flex items-center gap-2 mb-2 pr-8">
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
                    Cross-sections: {xsecs.length}
                  </span>
                  {selectedXsec !== null && (
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary">
                      {"\u00B7"} selected: {selectedXsec}
                    </span>
                  )}
                  <span className="flex-1" />
                  <span className="text-[11px] text-subtle-foreground">
                    {fileName}
                  </span>
                </div>

                {/* Zoom controls — only in maximized mode */}
                {xsecsMaximized && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] text-muted-foreground">Zoom:</span>
                    <input
                      type="range"
                      min="200"
                      max="8000"
                      step="100"
                      value={(() => {
                        if (zoomScale !== null) return zoomScale;
                        // Auto-fit: scale so selected (or largest) section fills ~80% height
                        const ref = selectedXsec !== null ? xsecs[selectedXsec] : null;
                        const maxDim = ref ? Math.max(ref.a, ref.b) : Math.max(...xsecs.map((x) => Math.max(x.a, x.b)));
                        return maxDim > 0 ? Math.min(8000, Math.round(150 / maxDim)) : 2000;
                      })()}
                      onChange={(e) => setZoomScale(parseInt(e.target.value))}
                      className="w-32 accent-primary"
                    />
                    <button
                      onClick={() => setZoomScale(null)}
                      className="rounded-full border border-border px-2 py-0.5 text-[9px] text-muted-foreground hover:text-foreground"
                    >
                      Fit
                    </button>
                    <span className="text-[9px] text-subtle-foreground">
                      {(() => {
                        if (zoomScale !== null) return `${zoomScale}x`;
                        const ref = selectedXsec !== null ? xsecs[selectedXsec] : null;
                        const maxDim = ref ? Math.max(ref.a, ref.b) : Math.max(...xsecs.map((x) => Math.max(x.a, x.b)));
                        return maxDim > 0 ? `${Math.min(8000, Math.round(150 / maxDim))}x (auto)` : "auto";
                      })()}
                    </span>
                  </div>
                )}

                {/* Cross-section ellipses strip */}
                <div className={`flex items-end gap-2 overflow-x-auto overflow-y-hidden pb-2 ${xsecsMaximized ? "flex-1 min-h-[80px]" : ""}`}>
                  {(() => {
                    let scale: number;
                    if (!xsecsMaximized) {
                      scale = 600;
                    } else if (zoomScale !== null) {
                      scale = zoomScale;
                    } else {
                      // Auto-fit: selected section (or largest) fills available space
                      const ref = selectedXsec !== null ? xsecs[selectedXsec] : null;
                      const maxDim = ref ? Math.max(ref.a, ref.b) : Math.max(...xsecs.map((x) => Math.max(x.a, x.b)));
                      scale = maxDim > 0 ? Math.min(8000, Math.round(150 / maxDim)) : 2000;
                    }
                    return xsecs.map((xsec, i) => {
                      const isSelected = selectedXsec === i;
                      return (
                        <button
                          key={i}
                          onClick={() => { if (xsecsMaximized) { setSelectedXsec(isSelected ? null : i); setZoomScale(null); } }}
                          className={`flex shrink-0 flex-col items-center justify-end gap-0.5 ${xsecsMaximized ? "cursor-pointer" : "cursor-default"}`}
                          title={`x=${xsec.xyz[0].toFixed(3)} a=${xsec.a.toFixed(3)} b=${xsec.b.toFixed(3)} n=${xsec.n.toFixed(1)}`}
                        >
                          <svg
                            width={Math.max(6, xsec.a * scale * 2)}
                            height={Math.max(6, xsec.b * scale * 2)}
                            viewBox={`${-xsec.a * scale} ${-xsec.b * scale} ${xsec.a * scale * 2} ${xsec.b * scale * 2}`}
                            className="shrink-0"
                          >
                            <path
                              d={superellipsePath(xsec.a * scale, xsec.b * scale, xsec.n)}
                              fill={isSelected ? "rgba(255,132,0,0.2)" : "rgba(255,132,0,0.1)"}
                              stroke={isSelected ? "#FF8400" : "rgba(255,132,0,0.4)"}
                              strokeWidth={isSelected ? 2 : 1}
                            />
                          </svg>
                          <span className={`shrink-0 text-[8px] ${isSelected ? "text-primary font-bold" : "text-subtle-foreground"}`}>
                            {i}
                          </span>
                        </button>
                      );
                    });
                  })()}
                </div>

                {/* Parameter editor — only in maximized mode with selection */}
                {xsecsMaximized && selectedXsec !== null && (() => {
                  const xsec = xsecs[selectedXsec];
                  const update = (field: keyof XSec, value: number, subIdx?: number) => {
                    setXsecs((prev) => prev.map((xs, i) => {
                      if (i !== selectedXsec) return xs;
                      if (field === "xyz" && subIdx !== undefined) {
                        const newXyz = [...xs.xyz];
                        newXyz[subIdx] = value;
                        return { ...xs, xyz: newXyz };
                      }
                      return { ...xs, [field]: value };
                    }));
                  };
                  return (
                    <div className="mt-3 border-t border-border pt-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-primary">
                          Section {selectedXsec} Parameters
                        </span>
                        <span className="flex-1" />
                        <button
                          onClick={() => setSelectedXsec(selectedXsec > 0 ? selectedXsec - 1 : null)}
                          disabled={selectedXsec <= 0}
                          className="flex size-6 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground disabled:opacity-30"
                        >
                          {"<"}
                        </button>
                        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
                          {selectedXsec + 1}/{xsecs.length}
                        </span>
                        <button
                          onClick={() => setSelectedXsec(selectedXsec < xsecs.length - 1 ? selectedXsec + 1 : null)}
                          disabled={selectedXsec >= xsecs.length - 1}
                          className="flex size-6 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground disabled:opacity-30"
                        >
                          {">"}
                        </button>
                      </div>
                      <div className="flex gap-3">
                        {(["x", "y", "z"] as const).map((axis, idx) => (
                          <div key={axis} className="flex flex-col gap-1">
                            <label className="text-[10px] text-muted-foreground">xyz[{axis}]</label>
                            <input
                              type="number"
                              step="0.001"
                              value={xsec.xyz[idx]}
                              onChange={(e) => update("xyz", parseFloat(e.target.value) || 0, idx)}
                              className="w-24 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground"
                            />
                          </div>
                        ))}
                        <div className="flex flex-col gap-1">
                          <label className="text-[10px] text-muted-foreground">a (semi-width)</label>
                          <input
                            type="number"
                            step="0.001"
                            value={xsec.a}
                            onChange={(e) => update("a", parseFloat(e.target.value) || 0.001)}
                            className="w-24 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <label className="text-[10px] text-muted-foreground">b (semi-height)</label>
                          <input
                            type="number"
                            step="0.001"
                            value={xsec.b}
                            onChange={(e) => update("b", parseFloat(e.target.value) || 0.001)}
                            className="w-24 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <label className="text-[10px] text-muted-foreground">n (exponent)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={xsec.n}
                            onChange={(e) => update("n", Math.max(0.5, Math.min(10, parseFloat(e.target.value) || 2)))}
                            className="w-24 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground"
                          />
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
              )}

              {/* Fuselage name (editable) — hidden when either view maximized */}
              {!viewerMaximized && !xsecsMaximized && (
              <div className="flex items-center gap-3">
                <label className="text-[11px] text-muted-foreground">Save as:</label>
                <input
                  type="text"
                  value={fuselageName}
                  onChange={(e) => setFuselageName(e.target.value)}
                  className="flex-1 rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                />
              </div>
              )}
            </div>
          )}
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
            onClick={onClose}
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
    </div>
  );
}
