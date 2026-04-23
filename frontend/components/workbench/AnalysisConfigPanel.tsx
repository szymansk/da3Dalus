"use client";

import { useState } from "react";
import { Play, RefreshCw, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import type { UseAnalysisReturn } from "@/hooks/useAnalysis";
import type { StripForcesAllParams } from "@/hooks/useStripForces";
import type { StreamlinesParams } from "@/hooks/useStreamlines";
import type { Tab } from "@/components/workbench/AnalysisViewerPanel";

type Mode = "single" | "sweep";

interface AnalysisConfigPanelProps {
  readonly activeTab: Tab;
  // Polar
  readonly analysis: UseAnalysisReturn;
  // Trefftz Plane
  readonly wingNames: string[];
  readonly selectedWing: string | null;
  readonly onRunStripForces?: (params: StripForcesAllParams) => void;
  readonly stripForcesRunning?: boolean;
  readonly stripForcesError?: string | null;
  // Streamlines
  readonly onRunStreamlines?: (params: StreamlinesParams) => void;
  readonly streamlinesRunning?: boolean;
  readonly streamlinesError?: string | null;
  // Modal close
  readonly onClose?: () => void;
}

function getIsRunning(activeTab: Tab, analysis: UseAnalysisReturn, stripForcesRunning: boolean | undefined, streamlinesRunning: boolean | undefined): boolean {
  if (activeTab === "Polar") return analysis.isRunning;
  if (activeTab === "Trefftz Plane") return stripForcesRunning ?? false;
  return streamlinesRunning ?? false;
}

function getCurrentError(activeTab: Tab, analysis: UseAnalysisReturn, stripForcesError: string | null | undefined, streamlinesError: string | null | undefined): string | null {
  if (activeTab === "Polar") return analysis.error;
  if (activeTab === "Trefftz Plane") return stripForcesError ?? null;
  return streamlinesError ?? null;
}

export function AnalysisConfigPanel({
  activeTab,
  analysis,
  wingNames: _wingNames,
  selectedWing: _selectedWing,
  onRunStripForces,
  stripForcesRunning,
  stripForcesError,
  onRunStreamlines,
  streamlinesRunning,
  streamlinesError,
  onClose,
}: Readonly<AnalysisConfigPanelProps>) {
  const [mode, setMode] = useState<Mode>("sweep");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // Shared form state
  const [alphaStart, setAlphaStart] = useState("-5");
  const [alphaEnd, setAlphaEnd] = useState("15");
  const [alphaStep, setAlphaStep] = useState("1");
  const [velocity, setVelocity] = useState("14");
  const [altitude, setAltitude] = useState("100");
  const [beta, setBeta] = useState("0");
  const [analysisTool, setAnalysisTool] = useState("aero_buildup");
  const [xyzRef, setXyzRef] = useState("0, 0, 0");

  // Trefftz-specific state
  const [trefftzAlpha, setTrefftzAlpha] = useState("5");

  const parseXyzRef = (): number[] => {
    const parts = xyzRef.split(",").map((s) => Number.parseFloat(s.trim()));
    return parts.length === 3 && parts.every((n) => !Number.isNaN(n))
      ? parts
      : [0, 0, 0];
  };

  // ── Polar handlers ──
  const handleRunPolar = () => {
    analysis.runAlphaSweep({
      analysis_tool: analysisTool,
      velocity_m_s: Number.parseFloat(velocity) || 14,
      alpha_start_deg: Number.parseFloat(alphaStart) || -5,
      alpha_end_deg: Number.parseFloat(alphaEnd) || 15,
      alpha_step_deg: Number.parseFloat(alphaStep) || 1,
      beta_deg: Number.parseFloat(beta) || 0,
      xyz_ref_m: parseXyzRef(),
    });
    onClose?.();
  };

  // ── Trefftz Plane handlers ──
  const handleRunStripForces = () => {
    onRunStripForces?.({
      velocity: Number.parseFloat(velocity) || 14,
      alpha: Number.parseFloat(trefftzAlpha) || 5,
      beta: Number.parseFloat(beta) || 0,
      altitude: Number.parseFloat(altitude) || 100,
      xyz_ref: parseXyzRef(),
    });
    onClose?.();
  };

  // ── Streamlines handlers ──
  const handleRunStreamlines = () => {
    onRunStreamlines?.({
      velocity: Number.parseFloat(velocity) || 14,
      alpha: Number.parseFloat(trefftzAlpha) || 5,
      beta: Number.parseFloat(beta) || 0,
      altitude: Number.parseFloat(altitude) || 100,
    });
    onClose?.();
  };

  const handleReset = () => {
    setAlphaStart("-5");
    setAlphaEnd("15");
    setAlphaStep("1");
    setVelocity("14");
    setAltitude("100");
    setBeta("0");
    setAnalysisTool("aero_buildup");
    setXyzRef("0, 0, 0");
    setTrefftzAlpha("5");
  };

  // Determine running/error state for active tab
  const isRunning = getIsRunning(activeTab, analysis, stripForcesRunning, streamlinesRunning);

  const currentError = getCurrentError(activeTab, analysis, stripForcesError, streamlinesError);

  const handleRun =
    activeTab === "Polar"
      ? handleRunPolar
      : activeTab === "Trefftz Plane"
        ? handleRunStripForces
        : handleRunStreamlines;

  return (
    <div className="flex w-full flex-col gap-4 overflow-y-auto">
      {/* ── Action Row ── */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleRun}
          disabled={isRunning}
          className="flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {isRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {isRunning ? "Running\u2026" : "Run Analysis"}
        </button>
        {activeTab === "Polar" && (
          <button
            onClick={() => {
              /* result is managed by the hook; parent can extend with clearResult */
            }}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3.5 py-2.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent"
          >
            <RefreshCw size={14} />
            Clear Results
          </button>
        )}
        <div className="flex-1" />
        <button
          onClick={handleReset}
          className="px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground transition-colors hover:text-foreground"
        >
          Reset to defaults
        </button>
      </div>

      {/* ── Error display ── */}
      {currentError && (
        <p className="rounded-xl border border-destructive bg-destructive/10 px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-destructive">
          {currentError}
        </p>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* POLAR TAB CONFIG                                                  */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Polar" && (
        <>
          {/* ── Operating Point Card ── */}
          <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
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
                  <label htmlFor="sweep-var-select" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                    sweep_var
                  </label>
                  <div className="relative">
                    <select id="sweep-var-select" className="w-full appearance-none rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
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
                    <label htmlFor="sweep-start" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                      start
                    </label>
                    <input
                      id="sweep-start"
                      type="text"
                      value={alphaStart}
                      onChange={(e) => setAlphaStart(e.target.value)}
                      className="rounded-xl border border-border bg-input px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label htmlFor="sweep-end" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                      end
                    </label>
                    <input
                      id="sweep-end"
                      type="text"
                      value={alphaEnd}
                      onChange={(e) => setAlphaEnd(e.target.value)}
                      className="rounded-xl border border-border bg-input px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label htmlFor="sweep-step" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                      step
                    </label>
                    <input
                      id="sweep-step"
                      type="text"
                      value={alphaStep}
                      onChange={(e) => setAlphaStep(e.target.value)}
                      className="rounded-xl border border-border bg-input px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
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
                    <label htmlFor="polar-velocity" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                      velocity
                    </label>
                    <div className="relative">
                      <input
                        id="polar-velocity"
                        type="text"
                        value={velocity}
                        onChange={(e) => setVelocity(e.target.value)}
                        className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-10 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                      />
                      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                        m/s
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label htmlFor="polar-altitude" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                      altitude
                    </label>
                    <div className="relative">
                      <input
                        id="polar-altitude"
                        type="text"
                        value={altitude}
                        onChange={(e) => setAltitude(e.target.value)}
                        className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                      />
                      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                        m
                      </span>
                    </div>
                  </div>
                </div>

                {/* Fixed row 2 */}
                <div className="flex flex-col gap-1">
                  <label htmlFor="polar-beta" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                    beta
                  </label>
                  <div className="relative">
                    <input
                      id="polar-beta"
                      type="text"
                      value={beta}
                      onChange={(e) => setBeta(e.target.value)}
                      className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
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
                            <label htmlFor={`advanced-${label}`} className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                              {label}
                            </label>
                            <div className="relative">
                              <input
                                id={`advanced-${label}`}
                                type="text"
                                defaultValue="0"
                                className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-12 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
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
                        <label htmlFor="polar-xyz-ref" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                          xyz_ref
                        </label>
                        <div className="relative">
                          <input
                            id="polar-xyz-ref"
                            type="text"
                            value={xyzRef}
                            onChange={(e) => setXyzRef(e.target.value)}
                            className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
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
          <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              Analysis Tool
            </span>

            {/* Tool select */}
            <div className="relative">
              <select
                value={analysisTool}
                onChange={(e) => setAnalysisTool(e.target.value)}
                className="w-full appearance-none rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
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
              <span className="rounded-full border border-border bg-card-muted px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                avl
              </span>
              <span className="rounded-full border border-border bg-card-muted px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                vortex_lattice
              </span>
            </div>

            {/* Flight profile */}
            <div className="flex flex-col gap-1">
              <label htmlFor="flight-profile-select" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                Flight profile
              </label>
              <div className="relative">
                <select id="flight-profile-select" className="w-full appearance-none rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
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
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* TREFFTZ PLANE TAB CONFIG                                         */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Trefftz Plane" && (
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
            Strip-Force Analysis (AVL)
          </span>

          {/* Alpha (single) */}
          <div className="flex flex-col gap-1">
            <label htmlFor="trefftz-alpha" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
              alpha
            </label>
            <div className="relative">
              <input
                id="trefftz-alpha"
                type="text"
                value={trefftzAlpha}
                onChange={(e) => setTrefftzAlpha(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                &deg;
              </span>
            </div>
          </div>

          {/* Velocity + Altitude */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label htmlFor="trefftz-velocity" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                velocity
              </label>
              <div className="relative">
                <input
                  id="trefftz-velocity"
                  type="text"
                  value={velocity}
                  onChange={(e) => setVelocity(e.target.value)}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-10 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  m/s
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="trefftz-altitude" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                altitude
              </label>
              <div className="relative">
                <input
                  id="trefftz-altitude"
                  type="text"
                  value={altitude}
                  onChange={(e) => setAltitude(e.target.value)}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  m
                </span>
              </div>
            </div>
          </div>

          {/* Beta */}
          <div className="flex flex-col gap-1">
            <label htmlFor="trefftz-beta" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
              beta
            </label>
            <div className="relative">
              <input
                id="trefftz-beta"
                type="text"
                value={beta}
                onChange={(e) => setBeta(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                &deg;
              </span>
            </div>
          </div>

          {/* Advanced section (xyz_ref) */}
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
                <div className="flex flex-col gap-1">
                  <label htmlFor="trefftz-xyz-ref" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                    xyz_ref
                  </label>
                  <div className="relative">
                    <input
                      id="trefftz-xyz-ref"
                      type="text"
                      value={xyzRef}
                      onChange={(e) => setXyzRef(e.target.value)}
                      className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
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

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* STREAMLINES TAB CONFIG                                           */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Streamlines" && (
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
            Streamline Computation
          </span>

          {/* Alpha (single) */}
          <div className="flex flex-col gap-1">
            <label htmlFor="streamlines-alpha" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
              alpha
            </label>
            <div className="relative">
              <input
                id="streamlines-alpha"
                type="text"
                value={trefftzAlpha}
                onChange={(e) => setTrefftzAlpha(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                &deg;
              </span>
            </div>
          </div>

          {/* Velocity + Altitude */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label htmlFor="streamlines-velocity" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                velocity
              </label>
              <div className="relative">
                <input
                  id="streamlines-velocity"
                  type="text"
                  value={velocity}
                  onChange={(e) => setVelocity(e.target.value)}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-10 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  m/s
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="streamlines-altitude" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                altitude
              </label>
              <div className="relative">
                <input
                  id="streamlines-altitude"
                  type="text"
                  value={altitude}
                  onChange={(e) => setAltitude(e.target.value)}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                  m
                </span>
              </div>
            </div>
          </div>

          {/* Beta */}
          <div className="flex flex-col gap-1">
            <label htmlFor="streamlines-beta" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
              beta
            </label>
            <div className="relative">
              <input
                id="streamlines-beta"
                type="text"
                value={beta}
                onChange={(e) => setBeta(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                &deg;
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
