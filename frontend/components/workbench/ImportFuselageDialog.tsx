"use client";

import { useState } from "react";
import { Upload, X, Check, Loader2, AlertTriangle, Maximize2, Minimize2 } from "lucide-react";

/**
 * MOCK — Import Fuselage Dialog
 *
 * This is a UI mock for user approval. It does NOT call the real
 * POST /fuselages/slice endpoint. All data is static/dummy.
 *
 * After approval, cad-modelling-service-hvi will wire real backend calls.
 */

interface ImportFuselageDialogProps {
  open: boolean;
  onClose: () => void;
  onAccept?: (fuselageName: string) => void;
}

// Dummy data for the mock
const MOCK_XSECS = Array.from({ length: 50 }, (_, i) => ({
  xyz: [i * 0.008, 0, 0],
  a: 0.005 + 0.04 * Math.sin((i / 49) * Math.PI),
  b: 0.005 + 0.03 * Math.sin((i / 49) * Math.PI),
  n: 2.0 + 0.5 * Math.sin((i / 49) * Math.PI),
}));

const MOCK_FIDELITY = { volume_ratio: 0.974, area_ratio: 0.983 };

type Phase = "upload" | "processing" | "preview";

export function ImportFuselageDialog({
  open,
  onClose,
  onAccept,
}: ImportFuselageDialogProps) {
  const [phase, setPhase] = useState<Phase>("upload");
  const [fileName, setFileName] = useState<string | null>(null);
  const [slices, setSlices] = useState(50);
  const [axis, setAxis] = useState("auto");
  const [fuselageName, setFuselageName] = useState("Imported Fuselage");
  const [viewerMaximized, setViewerMaximized] = useState(false);
  const [xsecsMaximized, setXsecsMaximized] = useState(false);

  if (!open) return null;

  const handleFileSelect = () => {
    // Mock: simulate file selection
    setFileName("e-Hawk Rumpf v29.step");
    setPhase("processing");
    // Simulate processing delay
    setTimeout(() => setPhase("preview"), 2000);
  };

  const handleAccept = () => {
    onAccept?.(fuselageName);
    handleReset();
    onClose();
  };

  const handleReset = () => {
    setPhase("upload");
    setFileName(null);
    setSlices(50);
    setAxis("auto");
    setFuselageName("Imported Fuselage");
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
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {phase === "upload" && (
            <div className="flex flex-col gap-5">
              {/* File drop zone */}
              <button
                onClick={handleFileSelect}
                className="flex h-40 flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border bg-card-muted hover:border-primary hover:bg-card-muted/80 transition-colors"
              >
                <Upload size={32} className="text-muted-foreground" />
                <span className="text-[14px] text-muted-foreground">
                  Click to select a STEP file
                </span>
                <span className="text-[11px] text-subtle-foreground">
                  Supported: .step, .stp
                </span>
              </button>

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
            <div className="flex flex-col gap-5">
              {/* Combined 3D viewer — hidden when cross-sections maximized */}
              {!xsecsMaximized && <div className="relative">
                <button
                  onClick={() => setViewerMaximized((m) => !m)}
                  className="absolute right-2 top-2 z-10 flex size-8 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                  title={viewerMaximized ? "Restore size" : "Maximize viewer"}
                >
                  {viewerMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>
                <div className={`relative flex items-center justify-center rounded-xl border border-border bg-[#17171A] ${viewerMaximized ? "h-[70vh]" : "h-64"}`}>
                  {/* Mock: overlaid fuselage shapes */}
                  <div className="relative">
                    <div
                      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[50%] opacity-30"
                      style={{ backgroundColor: "#3B82F6", width: 200, height: 80 }}
                    />
                    <div
                      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[50%] opacity-30"
                      style={{ backgroundColor: "#FF8400", width: 190, height: 76 }}
                    />
                    <div className="relative flex flex-col items-center gap-1 pt-16">
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                        3D Viewer Placeholder
                      </span>
                      <div className="flex items-center gap-4 mt-2">
                        <div className="flex items-center gap-1.5">
                          <div className="size-2.5 rounded-full" style={{ backgroundColor: "#3B82F6" }} />
                          <span className="text-[10px] text-muted-foreground">Original (STEP)</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <div className="size-2.5 rounded-full" style={{ backgroundColor: "#FF8400" }} />
                          <span className="text-[10px] text-muted-foreground">Reconstructed</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>}

              {/* Below elements hidden when viewer is maximized */}
              {!viewerMaximized && !xsecsMaximized && <>

              {/* Fidelity metrics */}
              <div className="flex gap-4">
                <div className="flex flex-1 items-center gap-3 rounded-xl border border-border bg-card-muted p-4">
                  <span className="text-[12px] text-muted-foreground">Volume Fidelity</span>
                  <span className="flex-1" />
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                    {(MOCK_FIDELITY.volume_ratio * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex flex-1 items-center gap-3 rounded-xl border border-border bg-card-muted p-4">
                  <span className="text-[12px] text-muted-foreground">Area Fidelity</span>
                  <span className="flex-1" />
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                    {(MOCK_FIDELITY.area_ratio * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Cross-section summary */}
              <div className={`relative rounded-xl border border-border bg-card-muted p-4 ${xsecsMaximized ? "flex-1" : ""}`}>
                <button
                  onClick={() => setXsecsMaximized((m) => !m)}
                  className="absolute right-2 top-2 z-10 flex size-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                  title={xsecsMaximized ? "Restore size" : "Maximize cross-sections"}
                >
                  {xsecsMaximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
                </button>
                <div className="flex items-center gap-2 mb-2 pr-8">
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
                    Cross-sections: {MOCK_XSECS.length}
                  </span>
                  <span className="flex-1" />
                  <span className="text-[11px] text-subtle-foreground">
                    {fileName}
                  </span>
                </div>
                <div className={`flex items-end gap-2 overflow-x-auto pb-2 ${xsecsMaximized ? "h-[50vh]" : ""}`}>
                  {(() => {
                    const scale = xsecsMaximized ? 2000 : 600;
                    return MOCK_XSECS.map((xsec, i) => (
                      <div
                        key={i}
                        className="flex shrink-0 flex-col items-center gap-0.5"
                        title={`x=${xsec.xyz[0].toFixed(3)} a=${xsec.a.toFixed(3)} b=${xsec.b.toFixed(3)} n=${xsec.n.toFixed(1)}`}
                      >
                        <div
                          className="rounded-full border border-primary/40"
                          style={{
                            width: Math.max(4, xsec.a * scale),
                            height: Math.max(4, xsec.b * scale),
                            backgroundColor: "rgba(255, 132, 0, 0.15)",
                          }}
                        />
                        <span className="text-[8px] text-subtle-foreground">
                          {i}
                        </span>
                      </div>
                    ));
                  })()}
                </div>
              </div>

              {/* Fuselage name (editable) */}
              <div className="flex items-center gap-3">
                <label className="text-[11px] text-muted-foreground">Save as:</label>
                <input
                  type="text"
                  value={fuselageName}
                  onChange={(e) => setFuselageName(e.target.value)}
                  className="flex-1 rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                />
              </div>
              </>}
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
              className="flex items-center gap-2 rounded-full bg-primary px-5 py-2 text-[13px] text-primary-foreground hover:opacity-90"
            >
              <Check size={14} />
              Accept & Save
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
