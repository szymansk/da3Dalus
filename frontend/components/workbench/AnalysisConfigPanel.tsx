"use client";

import { useState } from "react";
import { Play, RefreshCw, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import type { UseAnalysisReturn } from "@/hooks/useAnalysis";
import type { StripForcesAllParams } from "@/hooks/useStripForces";
import type { StreamlinesParams } from "@/hooks/useStreamlines";
import type { StoredOperatingPoint } from "@/hooks/useOperatingPoints";
import type { Tab } from "@/components/workbench/AnalysisViewerPanel";

type Mode = "single" | "sweep";
/**
 * gh-577: Trefftz/Streamlines basis selection.
 * - "trimmed" (default): pick a stored, trimmed OperatingPoint from the
 *   dropdown. Backend resolves α / xyz_ref / control deflections from it.
 * - "manual": diagnostic / component-analysis mode with free-form values.
 *   No trim guarantee — clearly labelled.
 */
type OpBasis = "trimmed" | "manual";

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
  // Default xyz_ref[0] for analysis runs — comes from the design CG
  // (cg_x effective value from assumptions). Falls back to 0 when not
  // available.
  readonly designCgX?: number | null;
  // gh-577: stored operating points for the trimmed-OP dropdown on the
  // Trefftz Plane and Streamlines tabs. The panel filters to TRIMMED
  // entries before rendering.
  readonly operatingPoints?: StoredOperatingPoint[];
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

/**
 * gh-577: Shared trim-basis chooser used by the Trefftz Plane and
 * Streamlines tabs. Extracted from `AnalysisConfigPanel` to keep the main
 * panel below the cognitive-complexity threshold (sonarjs/cognitive-complexity).
 */
function OperatingPointBasisSelector({
  opBasis,
  onChangeOpBasis,
  trimmedOps,
  effectiveOpId,
  onSelectOpId,
}: Readonly<{
  opBasis: OpBasis;
  onChangeOpBasis: (basis: OpBasis) => void;
  trimmedOps: StoredOperatingPoint[];
  effectiveOpId: number | null;
  onSelectOpId: (id: number) => void;
}>) {
  const radioKey = (basis: OpBasis) => (e: React.KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onChangeOpBasis(basis);
    }
  };
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
        Operating Point
      </span>
      <div className="flex items-center gap-4">
        <label className="flex cursor-pointer items-center gap-2">
          <span
            onClick={() => onChangeOpBasis("trimmed")}
            onKeyDown={radioKey("trimmed")}
            role="radio"
            aria-checked={opBasis === "trimmed"}
            tabIndex={0}
            className={`flex h-4 w-4 items-center justify-center rounded-full border-2 bg-background ${
              opBasis === "trimmed" ? "border-primary" : "border-border-strong"
            }`}
          >
            {opBasis === "trimmed" && (
              <span className="h-2 w-2 rounded-full bg-primary" />
            )}
          </span>
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
            Trimmed OP (recommended)
          </span>
        </label>
        <label className="flex cursor-pointer items-center gap-2">
          <span
            onClick={() => onChangeOpBasis("manual")}
            onKeyDown={radioKey("manual")}
            role="radio"
            aria-checked={opBasis === "manual"}
            tabIndex={0}
            className={`flex h-4 w-4 items-center justify-center rounded-full border-2 bg-background ${
              opBasis === "manual" ? "border-primary" : "border-border-strong"
            }`}
          >
            {opBasis === "manual" && (
              <span className="h-2 w-2 rounded-full bg-primary" />
            )}
          </span>
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
            Manual (untrimmed, diagnostic)
          </span>
        </label>
      </div>

      {opBasis === "trimmed" && (
        <TrimmedOpDropdown
          trimmedOps={trimmedOps}
          effectiveOpId={effectiveOpId}
          onSelectOpId={onSelectOpId}
        />
      )}

      {opBasis === "manual" && (
        <p className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[11px] text-amber-200">
          Diagnostic mode — the run uses the free-form inputs below with
          control surfaces at 0°. The resulting Trefftz wake / streamlines
          do not represent a trimmed flight condition.
        </p>
      )}
    </div>
  );
}

function TrimmedOpDropdown({
  trimmedOps,
  effectiveOpId,
  onSelectOpId,
}: Readonly<{
  trimmedOps: StoredOperatingPoint[];
  effectiveOpId: number | null;
  onSelectOpId: (id: number) => void;
}>) {
  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor="op-basis-select"
        className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground"
      >
        Trimmed operating point
      </label>
      {trimmedOps.length === 0 ? (
        <p className="rounded-xl border border-border bg-card-muted px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
          No trimmed operating points available. Trim one in the Operating
          Points tab, or switch to manual mode.
        </p>
      ) : (
        <div className="relative">
          <select
            id="op-basis-select"
            value={effectiveOpId ?? ""}
            onChange={(e) => onSelectOpId(Number.parseInt(e.target.value, 10))}
            className="w-full appearance-none rounded-xl border border-border bg-input px-3 py-2 pr-8 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
          >
            {trimmedOps.map((op) => (
              <option key={op.id} value={op.id}>
                {op.name} — α={(op.alpha * (180 / Math.PI)).toFixed(2)}°, V=
                {op.velocity.toFixed(1)} m/s
              </option>
            ))}
          </select>
          <ChevronDown
            size={14}
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
        </div>
      )}
      <p className="font-[family-name:var(--font-geist-sans)] text-[10px] italic text-subtle-foreground">
        α, xyz_ref, velocity, altitude, and control-surface deflections are
        taken from the selected trim solution (gh-577).
      </p>
    </div>
  );
}

export function AnalysisConfigPanel({
  activeTab,
  analysis,
  // wingNames, selectedWing reserved for future per-wing analysis

  onRunStripForces,
  stripForcesRunning,
  stripForcesError,
  onRunStreamlines,
  streamlinesRunning,
  streamlinesError,
  designCgX,
  operatingPoints,
  onClose,
}: Readonly<AnalysisConfigPanelProps>) {
  const [mode, setMode] = useState<Mode>("sweep");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // gh-577: Trefftz/Streamlines basis. Default "trimmed" so the wake and
  // induced drag reflect a flight condition the aircraft can actually
  // hold. "manual" is an explicit opt-in to an untrimmed diagnostic run.
  const [opBasis, setOpBasis] = useState<OpBasis>("trimmed");
  const trimmedOps = (operatingPoints ?? []).filter(
    (op) => op.status === "TRIMMED",
  );
  // User-chosen OP, or null = no explicit choice yet. The effective id
  // falls back to the first trimmed OP so the dropdown always has a
  // sensible default once data arrives (no state mirroring needed).
  const [chosenOpId, setChosenOpId] = useState<number | null>(null);
  const effectiveOpId =
    chosenOpId ?? (trimmedOps.length > 0 ? trimmedOps[0].id : null);

  // Shared form state
  const [alphaStart, setAlphaStart] = useState("-5");
  const [alphaEnd, setAlphaEnd] = useState("15");
  const [alphaStep, setAlphaStep] = useState("1");
  const [velocity, setVelocity] = useState("14");
  const [altitude, setAltitude] = useState("100");
  const [beta, setBeta] = useState("0");
  const [analysisTool, setAnalysisTool] = useState("aero_buildup");
  // xyzRef defaults to the design CG (cg_x effective from assumptions)
  // — that is the moment-reference point the rest of the system uses.
  // Falling back to "0, 0, 0" is just a placeholder until the prop arrives.
  const [xyzRef, setXyzRef] = useState(
    designCgX != null ? `${designCgX.toFixed(4)}, 0, 0` : "0, 0, 0",
  );

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
    const start = Number.parseFloat(alphaStart) || -5;
    const end = Number.parseFloat(alphaEnd) || 15;
    const step = Number.parseFloat(alphaStep) || 1;
    analysis.runAlphaSweep({
      alpha_start: start,
      alpha_end: end,
      alpha_num: Math.max(2, Math.round((end - start) / step) + 1),
      velocity: Number.parseFloat(velocity) || 14,
      beta: Number.parseFloat(beta) || 0,
      altitude: Number.parseFloat(altitude) || 0,
      xyz_ref: parseXyzRef(),
    });
    onClose?.();
  };

  // gh-577: when running on a trimmed OP we send `operating_point_id`
  // and the backend overrides α/xyz_ref/control deflections from the
  // stored record. Inline values still go on the wire as a fallback in
  // case the OP cannot be resolved server-side.
  const useTrimmedOp =
    opBasis === "trimmed" && effectiveOpId !== null;

  // ── Trefftz Plane handlers ──
  const handleRunStripForces = () => {
    onRunStripForces?.({
      velocity: Number.parseFloat(velocity) || 14,
      alpha: Number.parseFloat(trefftzAlpha) || 5,
      beta: Number.parseFloat(beta) || 0,
      altitude: Number.parseFloat(altitude) || 100,
      xyz_ref: parseXyzRef(),
      operating_point_id: useTrimmedOp ? effectiveOpId : null,
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
      xyz_ref: parseXyzRef(),
      operating_point_id: useTrimmedOp ? effectiveOpId : null,
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
    setXyzRef(designCgX != null ? `${designCgX.toFixed(4)}, 0, 0` : "0, 0, 0");
    setTrefftzAlpha("5");
  };

  // Determine running/error state for active tab
  const isRunning = getIsRunning(activeTab, analysis, stripForcesRunning, streamlinesRunning);

  const currentError = getCurrentError(activeTab, analysis, stripForcesError, streamlinesError);

  let handleRun = handleRunStreamlines;
  if (activeTab === "Polar") handleRun = handleRunPolar;
  else if (activeTab === "Trefftz Plane") handleRun = handleRunStripForces;

  const opBasisSelector = (
    <OperatingPointBasisSelector
      opBasis={opBasis}
      onChangeOpBasis={setOpBasis}
      trimmedOps={trimmedOps}
      effectiveOpId={effectiveOpId}
      onSelectOpId={setChosenOpId}
    />
  );

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
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setMode("single"); } }}
                  role="radio"
                  aria-checked={mode === "single"}
                  tabIndex={0}
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
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setMode("sweep"); } }}
                  role="radio"
                  aria-checked={mode === "sweep"}
                  tabIndex={0}
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
        <>
          {opBasisSelector}
          <div
            className={`flex flex-col gap-3 rounded-xl border border-border bg-card p-4 ${
              useTrimmedOp ? "opacity-50" : ""
            }`}
          >
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
            Strip-Force Analysis (AVL) {useTrimmedOp ? "— overridden by trimmed OP" : ""}
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
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* STREAMLINES TAB CONFIG                                           */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Streamlines" && (
        <>
          {opBasisSelector}
          <div
            className={`flex flex-col gap-3 rounded-xl border border-border bg-card p-4 ${
              useTrimmedOp ? "opacity-50" : ""
            }`}
          >
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
            Streamline Computation {useTrimmedOp ? "— overridden by trimmed OP" : ""}
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
        </>
      )}
    </div>
  );
}
