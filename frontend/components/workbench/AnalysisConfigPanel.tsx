"use client";

import { useState } from "react";
import { Play, RefreshCw, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import type { UseAnalysisReturn } from "@/hooks/useAnalysis";

type Mode = "single" | "sweep";

export function AnalysisConfigPanel({ analysis }: { analysis: UseAnalysisReturn }) {
  const [mode, setMode] = useState<Mode>("sweep");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // Form state
  const [alphaStart, setAlphaStart] = useState("-5.0");
  const [alphaEnd, setAlphaEnd] = useState("15.0");
  const [alphaStep, setAlphaStep] = useState("1.0");
  const [velocity, setVelocity] = useState("14.0");
  const [altitude, setAltitude] = useState("100");
  const [beta, setBeta] = useState("0.0");
  const [analysisTool, setAnalysisTool] = useState("aero_buildup");
  const [xyzRef, setXyzRef] = useState("0.0, 0.0, 0.0");

  const handleRun = () => {
    const xyzParts = xyzRef.split(",").map((s) => parseFloat(s.trim()));
    const xyz = xyzParts.length === 3 && xyzParts.every((n) => !isNaN(n))
      ? xyzParts
      : [0, 0, 0];

    analysis.runAlphaSweep({
      analysis_tool: analysisTool,
      velocity_m_s: parseFloat(velocity) || 14.0,
      alpha_start_deg: parseFloat(alphaStart) || -5.0,
      alpha_end_deg: parseFloat(alphaEnd) || 15.0,
      alpha_step_deg: parseFloat(alphaStep) || 1.0,
      beta_deg: parseFloat(beta) || 0.0,
      xyz_ref_m: xyz,
    });
  };

  const handleReset = () => {
    setAlphaStart("-5.0");
    setAlphaEnd("15.0");
    setAlphaStep("1.0");
    setVelocity("14.0");
    setAltitude("100");
    setBeta("0.0");
    setAnalysisTool("aero_buildup");
    setXyzRef("0.0, 0.0, 0.0");
  };

  return (
    <div className="flex w-full flex-col gap-4 overflow-y-auto">
      {/* ── Action Row ── */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleRun}
          disabled={analysis.isRunning}
          className="flex items-center gap-2 rounded-[--radius-pill] bg-primary px-4 py-2.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {analysis.isRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {analysis.isRunning ? "Running\u2026" : "Run Analysis"}
        </button>
        <button
          onClick={() => {
            /* result is managed by the hook; parent can extend with clearResult */
          }}
          className="flex items-center gap-1.5 rounded-[--radius-pill] border border-border bg-card-muted px-3.5 py-2.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent"
        >
          <RefreshCw size={14} />
          Clear Results
        </button>
        <button
          disabled
          className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Load OP set&hellip;
        </button>
        <div className="flex-1" />
        <button
          onClick={handleReset}
          className="px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground transition-colors hover:text-foreground"
        >
          Reset to defaults
        </button>
      </div>

      {/* ── Error display ── */}
      {analysis.error && (
        <p className="rounded-[--radius-s] border border-destructive bg-destructive/10 px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-destructive">
          {analysis.error}
        </p>
      )}

      {/* ── Operating Point Card ── */}
      <div className="flex flex-col gap-3 rounded-[--radius-m] border border-border bg-card p-4">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Operating Point
        </span>

        {/* Radio row */}
        <div className="flex items-center gap-4">
          <label className="flex cursor-pointer items-center gap-2">
            <span
              onClick={() => setMode("single")}
              className={`flex h-4 w-4 items-center justify-center rounded-full border-2 bg-background ${
                mode === "single" ? "border-primary" : "border-border-strong"
              }`}
            >
              {mode === "single" && (
                <span className="h-2 w-2 rounded-full bg-primary" />
              )}
            </span>
            <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
              Single Point
            </span>
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <span
              onClick={() => setMode("sweep")}
              className={`flex h-4 w-4 items-center justify-center rounded-full border-2 bg-background ${
                mode === "sweep" ? "border-primary" : "border-border-strong"
              }`}
            >
              {mode === "sweep" && (
                <span className="h-2 w-2 rounded-full bg-primary" />
              )}
            </span>
            <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
              Parameter Sweep
            </span>
          </label>
        </div>

        {/* Sweep fields (shown when Parameter Sweep is selected) */}
        {mode === "sweep" && (
          <div className="flex flex-col gap-3">
            {/* sweep_var */}
            <div className="flex flex-col gap-1">
              <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                sweep_var
              </label>
              <div className="relative">
                <select className="w-full appearance-none rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
                  <option>alpha</option>
                  <option>beta</option>
                  <option>velocity</option>
                </select>
                <ChevronDown
                  size={14}
                  className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
              </div>
            </div>

            {/* Range row */}
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  start
                </label>
                <input
                  type="text"
                  value={alphaStart}
                  onChange={(e) => setAlphaStart(e.target.value)}
                  className="rounded-[--radius-s] border border-border bg-input px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  end
                </label>
                <input
                  type="text"
                  value={alphaEnd}
                  onChange={(e) => setAlphaEnd(e.target.value)}
                  className="rounded-[--radius-s] border border-border bg-input px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  step
                </label>
                <input
                  type="text"
                  value={alphaStep}
                  onChange={(e) => setAlphaStep(e.target.value)}
                  className="rounded-[--radius-s] border border-border bg-input px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
              </div>
            </div>

            {/* Divider with "Fixed values" */}
            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-subtle-foreground">
                Fixed values
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* Fixed row 1 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  velocity
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={velocity}
                    onChange={(e) => setVelocity(e.target.value)}
                    className="w-full rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-10 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                  />
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                    m/s
                  </span>
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  altitude
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={altitude}
                    onChange={(e) => setAltitude(e.target.value)}
                    className="w-full rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                  />
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                    m
                  </span>
                </div>
              </div>
            </div>

            {/* Fixed row 2 */}
            <div className="flex flex-col gap-1">
              <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                beta
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={beta}
                  onChange={(e) => setBeta(e.target.value)}
                  className="w-full rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  &deg;
                </span>
              </div>
            </div>

            {/* Advanced section */}
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setAdvancedOpen(!advancedOpen)}
                className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground transition-colors hover:text-foreground"
              >
                {advancedOpen ? (
                  <ChevronDown size={12} />
                ) : (
                  <ChevronRight size={12} />
                )}
                Advanced
              </button>
              {advancedOpen && (
                <div className="flex flex-col gap-3 opacity-60">
                  {/* p/q/r row */}
                  <div className="grid grid-cols-3 gap-3">
                    {["p", "q", "r"].map((label) => (
                      <div key={label} className="flex flex-col gap-1">
                        <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                          {label}
                        </label>
                        <div className="relative">
                          <input
                            type="text"
                            defaultValue="0.0"
                            className="w-full rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-12 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                          />
                          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                            rad/s
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* xyz_ref row */}
                  <div className="flex flex-col gap-1">
                    <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                      xyz_ref
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={xyzRef}
                        onChange={(e) => setXyzRef(e.target.value)}
                        className="w-full rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                      />
                      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                        m
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Analysis Tool Card ── */}
      <div className="flex flex-col gap-3 rounded-[--radius-m] border border-border bg-card p-4">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Analysis Tool
        </span>

        {/* Tool select */}
        <div className="relative">
          <select
            value={analysisTool}
            onChange={(e) => setAnalysisTool(e.target.value)}
            className="w-full appearance-none rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
          >
            <option value="aero_buildup">aerobuildup</option>
            <option value="avl">avl</option>
            <option value="vortex_lattice">vortex_lattice</option>
          </select>
          <ChevronDown
            size={14}
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
        </div>

        {/* Tool chips */}
        <div className="flex items-center gap-2">
          <span className="rounded-[--radius-pill] border border-border bg-card-muted px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            avl
          </span>
          <span className="rounded-[--radius-pill] border border-border bg-card-muted px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            vortex_lattice
          </span>
        </div>

        {/* Flight profile */}
        <div className="flex flex-col gap-1">
          <label className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
            Flight profile
          </label>
          <div className="relative">
            <select className="w-full appearance-none rounded-[--radius-s] border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
              <option>cruise</option>
              <option>takeoff</option>
              <option>landing</option>
            </select>
            <ChevronDown
              size={14}
              className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
          </div>
        </div>

        {/* Footer text */}
        <p className="font-[family-name:var(--font-geist-sans)] text-[10px] italic text-subtle-foreground">
          AVL: single point only &middot; AeroBuildup / VLM: sweeps supported
        </p>
      </div>
    </div>
  );
}
