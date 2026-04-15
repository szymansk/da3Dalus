"use client";

import { useState } from "react";
import { Upload, X, Check, Loader2, AlertTriangle } from "lucide-react";

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
const MOCK_XSECS = Array.from({ length: 12 }, (_, i) => ({
  xyz: [i * 0.03, 0, 0],
  a: 0.01 + 0.04 * Math.sin((i / 11) * Math.PI),
  b: 0.01 + 0.03 * Math.sin((i / 11) * Math.PI),
  n: 2.0 + 0.5 * Math.sin((i / 11) * Math.PI),
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
        className="flex w-[900px] max-h-[80vh] flex-col rounded-2xl border border-border bg-card shadow-2xl"
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
              {/* Dual visualization placeholder */}
              <div className="flex gap-4">
                {/* Original */}
                <div className="flex flex-1 flex-col gap-2">
                  <span className="text-[11px] text-muted-foreground">
                    Original Geometry
                  </span>
                  <div className="flex h-48 items-center justify-center rounded-xl border border-border bg-card-muted">
                    <div className="flex flex-col items-center gap-2">
                      <div
                        className="h-16 w-40 rounded-full opacity-50"
                        style={{ backgroundColor: "#3B82F6" }}
                      />
                      <span className="text-[10px] text-subtle-foreground">
                        STEP mesh (blue, transparent)
                      </span>
                    </div>
                  </div>
                </div>
                {/* Reconstructed */}
                <div className="flex flex-1 flex-col gap-2">
                  <span className="text-[11px] text-muted-foreground">
                    Reconstructed (Superellipses)
                  </span>
                  <div className="flex h-48 items-center justify-center rounded-xl border border-border bg-card-muted">
                    <div className="flex flex-col items-center gap-2">
                      <div
                        className="h-16 w-40 rounded-full opacity-50"
                        style={{ backgroundColor: "#FF8400" }}
                      />
                      <span className="text-[10px] text-subtle-foreground">
                        Superellipse loft (orange, transparent)
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Info: these will be overlaid in the real implementation */}
              <div className="flex items-start gap-2 rounded-xl border border-border bg-card-muted p-3">
                <AlertTriangle size={14} className="mt-0.5 shrink-0 text-primary" />
                <span className="text-[11px] text-muted-foreground">
                  Mock: In the final version, both geometries will be overlaid
                  in a single 3D viewer (blue = original, orange = reconstructed,
                  both semi-transparent).
                </span>
              </div>

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
              <div className="rounded-xl border border-border bg-card-muted p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
                    Cross-sections: {MOCK_XSECS.length}
                  </span>
                  <span className="flex-1" />
                  <span className="text-[11px] text-subtle-foreground">
                    {fileName}
                  </span>
                </div>
                <div className="flex gap-1 overflow-x-auto">
                  {MOCK_XSECS.map((xsec, i) => (
                    <div
                      key={i}
                      className="flex shrink-0 flex-col items-center gap-0.5"
                      title={`x=${xsec.xyz[0].toFixed(3)} a=${xsec.a.toFixed(3)} b=${xsec.b.toFixed(3)} n=${xsec.n.toFixed(1)}`}
                    >
                      <div
                        className="rounded-full border border-primary/40"
                        style={{
                          width: Math.max(4, xsec.a * 600),
                          height: Math.max(4, xsec.b * 600),
                          backgroundColor: "rgba(255, 132, 0, 0.15)",
                        }}
                      />
                      <span className="text-[8px] text-subtle-foreground">
                        {i}
                      </span>
                    </div>
                  ))}
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
