"use client";

/**
 * PowertrainSizingModal (gh-197)
 *
 * Interactive dialog that guides the designer through the electric powertrain
 * sizing process, following the Roxxy Motoren Fibel methodology:
 *
 *   https://www.multiplex-rc.de/userdata/filegallery/original/87_roxxy-motoren-fibel-web.pdf
 *
 * The modal:
 *  1. Pre-fills parameters from the aeroplane's analysis context (gh-924):
 *       - cd0, s_ref_m2 (from ASB)
 *       - altitude, eta_prop, eta_motor (editable defaults)
 *  2. Displays the brushless_motor catalog filtered from the component library.
 *  3. The user picks a motor → motor efficiency is pre-filled from specs.efficiency_pct.
 *  4. On "Run Sizing", calls POST /powertrain/sizing with the current params.
 *  5. Shows the top recommendations sorted by confidence.
 *  6. On "Add to Component Tree", adds the chosen motor (and ESC if matched)
 *     as cots nodes at the tree root.
 *
 * Prop-finder (#199 / #615) is out of scope — eta_prop is an editable field.
 */

import { useState, useCallback, useEffect } from "react";
import { X, Loader2, AlertTriangle, ExternalLink, Check, Zap } from "lucide-react";
import {
  usePowertrainModalParams,
  runPowertrainSizing,
  type MotorSuggestion,
  type PowertrainCandidate,
} from "@/hooks/usePowertrainSizingModal";
import { useMissionObjectives } from "@/hooks/useMissionObjectives";
import { addTreeNode } from "@/hooks/useComponentTree";
import { useDialog } from "@/hooks/useDialog";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ROXXY_FIBEL_URL =
  "https://www.multiplex-rc.de/userdata/filegallery/original/87_roxxy-motoren-fibel-web.pdf";

// Default mission parameters when not available from context
const DEFAULT_CRUISE_MPS = 15.0;
const DEFAULT_TOP_SPEED_MPS = 25.0;
const DEFAULT_FLIGHT_TIME_MIN = 15.0;
const DEFAULT_AIRFRAME_MASS_KG = 1.5;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly aeroplaneId: string;
  readonly onTreeMutate: () => void;
}

// ---------------------------------------------------------------------------
// NumericField — a small labeled numeric input
// ---------------------------------------------------------------------------

interface NumericFieldProps {
  readonly label: string;
  readonly value: number;
  readonly onChange: (v: number) => void;
  readonly step?: number;
  readonly min?: number;
  readonly max?: number;
  readonly unit?: string;
  readonly readOnly?: boolean;
  readonly testId?: string;
}

function NumericField({
  label,
  value,
  onChange,
  step = 0.01,
  min,
  max,
  unit,
  readOnly = false,
  testId,
}: NumericFieldProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
        {label}
      </span>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          step={step}
          min={min}
          max={max}
          readOnly={readOnly}
          onChange={(e) => {
            const n = parseFloat(e.target.value);
            if (!Number.isNaN(n)) onChange(n);
          }}
          className={`w-24 rounded border border-border px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground ${
            readOnly
              ? "bg-sidebar-accent text-muted-foreground"
              : "bg-card-muted"
          }`}
          data-testid={testId}
        />
        {unit && (
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MotorRow — one row in the motor picker list
// ---------------------------------------------------------------------------

interface MotorRowProps {
  readonly motor: MotorSuggestion;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
}

function MotorRow({ motor, isSelected, onSelect }: MotorRowProps) {
  return (
    <tr
      onClick={onSelect}
      className={`cursor-pointer border-b border-border/50 font-[family-name:var(--font-jetbrains-mono)] text-[11px] transition-colors hover:bg-sidebar-accent ${
        isSelected ? "bg-orange-500/10" : ""
      }`}
      data-testid={`motor-row-${motor.id}`}
      aria-selected={isSelected}
    >
      <td className="py-1.5 pr-3">
        {isSelected && (
          <Check size={10} className="inline text-orange-400" />
        )}
      </td>
      <td className="py-1.5 pr-3 font-semibold text-foreground">{motor.name}</td>
      <td className="py-1.5 pr-3 text-muted-foreground">{motor.manufacturer ?? "—"}</td>
      <td className="py-1.5 pr-3 text-foreground">
        {motor.kv != null ? `${Math.round(motor.kv)} KV` : "—"}
      </td>
      <td className="py-1.5 pr-3 text-foreground">
        {motor.max_power_w != null ? `${Math.round(motor.max_power_w)} W` : "—"}
      </td>
      <td className="py-1.5 pr-3 text-foreground">
        {motor.efficiency_pct.toFixed(0)}%
      </td>
      <td className="py-1.5 text-muted-foreground">
        {motor.mass_g != null ? `${motor.mass_g}g` : "—"}
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// CandidateRow — one row in the results table
// ---------------------------------------------------------------------------

/** Map a confidence 0–100 value to a Tailwind class string for the badge. */
function confidenceClass(conf: number): string {
  if (conf >= 60) return "bg-emerald-900/40 text-emerald-400";
  if (conf >= 30) return "bg-orange-900/40 text-orange-400";
  return "bg-zinc-800 text-muted-foreground";
}

interface CandidateRowProps {
  readonly candidate: PowertrainCandidate;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
}

function CandidateRow({ candidate, isSelected, onSelect }: CandidateRowProps) {
  const conf = Math.round(candidate.confidence * 100);
  return (
    <tr
      onClick={onSelect}
      className={`cursor-pointer border-b border-border/50 font-[family-name:var(--font-jetbrains-mono)] text-[11px] transition-colors hover:bg-sidebar-accent ${
        isSelected ? "bg-orange-500/10" : ""
      }`}
      data-testid={`candidate-row-${candidate.motor_id ?? "nomoby"}-${candidate.battery_id ?? "nobat"}`}
      aria-selected={isSelected}
    >
      <td className="py-1.5 pr-3">
        {isSelected && <Check size={10} className="inline text-orange-400" />}
      </td>
      <td className="py-1.5 pr-3 text-foreground">{candidate.motor_name ?? "—"}</td>
      <td className="py-1.5 pr-3 text-muted-foreground">{candidate.esc_name ?? "—"}</td>
      <td className="py-1.5 pr-3 text-muted-foreground">{candidate.battery_name ?? "—"}</td>
      <td className="py-1.5 pr-3 text-emerald-400">
        {candidate.estimated_flight_time_min.toFixed(1)} min
      </td>
      <td className="py-1.5 pr-3 text-foreground">
        {candidate.estimated_cruise_power_w.toFixed(0)} W
      </td>
      <td className="py-1.5">
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-[9px] ${confidenceClass(conf)}`}
        >
          {conf}%
        </span>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main PowertrainSizingModal
// ---------------------------------------------------------------------------

export function PowertrainSizingModal({
  open,
  onClose,
  aeroplaneId,
  onTreeMutate,
}: Props) {
  const { dialogRef, handleClose } = useDialog(open, onClose);

  // Fetch pre-filled defaults
  const { data: defaults, isLoading: defaultsLoading, error: defaultsError } =
    usePowertrainModalParams(open ? aeroplaneId : null);

  // Fetch mission for cruise speed / mass defaults
  const { data: mission } = useMissionObjectives(open ? aeroplaneId : null);

  // ---------------------------------------------------------------------------
  // Form state — initialized from defaults when they arrive
  // ---------------------------------------------------------------------------
  const [altitude, setAltitude] = useState(0.0);
  const [cd0, setCd0] = useState(0.03);
  const [etaProp, setEtaProp] = useState(0.65);
  const [etaMotor, setEtaMotor] = useState(0.85);
  const [airframeMass, setAirframeMass] = useState(DEFAULT_AIRFRAME_MASS_KG);
  const [cruiseSpeed, setCruiseSpeed] = useState(DEFAULT_CRUISE_MPS);
  const [topSpeed, setTopSpeed] = useState(DEFAULT_TOP_SPEED_MPS);
  const [flightTime, setFlightTime] = useState(DEFAULT_FLIGHT_TIME_MIN);

  // Initialize form when defaults arrive (only once on open)
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (open && defaults && !initialized) {
      setAltitude(defaults.altitude_m);
      setCd0(defaults.cd0);
      setEtaProp(defaults.eta_prop);
      setEtaMotor(defaults.eta_motor);
      setInitialized(true);
    }
    if (!open) {
      setInitialized(false);
    }
  }, [open, defaults, initialized]);

  // Pre-fill mission cruise speed when mission loads
  useEffect(() => {
    if (open && mission?.target_cruise_mps && !initialized) {
      setCruiseSpeed(mission.target_cruise_mps);
      setTopSpeed(Math.round(mission.target_cruise_mps * 1.5 * 10) / 10);
    }
  }, [open, mission, initialized]);

  // ---------------------------------------------------------------------------
  // Motor picker
  // ---------------------------------------------------------------------------
  const [selectedMotorId, setSelectedMotorId] = useState<number | null>(null);
  const [motorSearch, setMotorSearch] = useState("");

  const handleSelectMotor = useCallback(
    (m: MotorSuggestion) => {
      setSelectedMotorId(m.id);
      setEtaMotor(m.efficiency_pct / 100);
    },
    []
  );

  const filteredMotors = (defaults?.motors ?? []).filter(
    (m) =>
      !motorSearch ||
      m.name.toLowerCase().includes(motorSearch.toLowerCase()) ||
      (m.manufacturer ?? "").toLowerCase().includes(motorSearch.toLowerCase())
  );

  // ---------------------------------------------------------------------------
  // Sizing run
  // ---------------------------------------------------------------------------
  const [candidates, setCandidates] = useState<PowertrainCandidate[]>([]);
  const [sizingWarnings, setSizingWarnings] = useState<string[]>([]);
  const [sizing, setSizing] = useState(false);
  const [sizingError, setSizingError] = useState<string | null>(null);

  const handleRunSizing = useCallback(async () => {
    setSizing(true);
    setSizingError(null);
    try {
      const result = await runPowertrainSizing(aeroplaneId, {
        airframe_mass_kg: airframeMass,
        target_cruise_speed_ms: cruiseSpeed,
        target_top_speed_ms: topSpeed > cruiseSpeed ? topSpeed : cruiseSpeed * 1.5,
        target_flight_time_min: flightTime,
        altitude_m: altitude,
        cd0,
        s_ref_m2: defaults?.s_ref_m2,
        eta_prop: etaProp,
        eta_motor: etaMotor,
      });
      setCandidates(result.recommendations);
      setSizingWarnings(result.warnings);
    } catch (err) {
      setSizingError(err instanceof Error ? err.message : "Sizing failed");
    } finally {
      setSizing(false);
    }
  }, [
    aeroplaneId,
    airframeMass,
    cruiseSpeed,
    topSpeed,
    flightTime,
    altitude,
    cd0,
    defaults?.s_ref_m2,
    etaProp,
    etaMotor,
  ]);

  // ---------------------------------------------------------------------------
  // Candidate selection + add to tree
  // ---------------------------------------------------------------------------
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const handleAddToTree = useCallback(async () => {
    if (selectedCandidateIdx == null) return;
    const candidate = candidates[selectedCandidateIdx];
    if (!candidate) return;

    setAdding(true);
    setAddError(null);
    try {
      // Add motor node (cots)
      if (candidate.motor_id != null) {
        await addTreeNode(aeroplaneId, {
          node_type: "cots",
          name: candidate.motor_name ?? "Motor",
          component_id: candidate.motor_id,
          quantity: 1,
        });
      }
      // Add ESC node (cots) if matched
      if (candidate.esc_id != null) {
        await addTreeNode(aeroplaneId, {
          node_type: "cots",
          name: candidate.esc_name ?? "ESC",
          component_id: candidate.esc_id,
          quantity: 1,
        });
      }
      onTreeMutate();
      onClose();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Add to tree failed");
    } finally {
      setAdding(false);
    }
  }, [aeroplaneId, candidates, selectedCandidateIdx, onTreeMutate, onClose]);

  // ---------------------------------------------------------------------------
  // s_ref display (read-only)
  // ---------------------------------------------------------------------------
  const sRefDisplay = defaults?.s_ref_m2 ?? null;

  // ---------------------------------------------------------------------------
  // Warnings: combine defaults warnings + sizing warnings
  // ---------------------------------------------------------------------------
  const allWarnings = [
    ...(defaults?.warnings ?? []),
    ...sizingWarnings,
  ];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label="Powertrain Sizing"
    >
      <div
        className="flex max-h-[90vh] w-[780px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
        data-testid="powertrain-sizing-modal"
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <Zap size={16} className="text-orange-400" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            Powertrain Sizing
          </span>
          <span className="flex-1" />
          <a
            href={ROXXY_FIBEL_URL}
            target="_blank"
            rel="noopener noreferrer"
            title="Roxxy Motoren Fibel — sizing reference"
            className="flex items-center gap-1 rounded-full border border-border px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            data-testid="roxxy-fibel-link"
          >
            <ExternalLink size={11} />
            Roxxy Fibel
          </a>
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            aria-label="Close"
            data-testid="modal-close-btn"
          >
            <X size={16} />
          </button>
        </div>

        {/* Loading state */}
        {defaultsLoading && (
          <div className="flex items-center gap-2 py-4 text-muted-foreground">
            <Loader2 size={14} className="animate-spin" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[12px]">
              Loading aero parameters…
            </span>
          </div>
        )}

        {/* Defaults error */}
        {defaultsError && !defaultsLoading && (
          <div className="flex items-center gap-2 rounded-lg border border-orange-500/30 bg-orange-900/20 px-3 py-2">
            <AlertTriangle size={12} className="text-orange-400" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-orange-400">
              Could not load aero parameters. Using defaults.
            </span>
          </div>
        )}

        {/* Warnings banner */}
        {allWarnings.length > 0 && (
          <div
            className="rounded-lg border border-orange-500/30 bg-orange-900/20 px-3 py-2"
            data-testid="modal-warnings"
          >
            {allWarnings.map((w) => (
              <p
                key={w}
                className="font-[family-name:var(--font-geist-sans)] text-[10px] text-orange-400"
              >
                ⚠ {w}
              </p>
            ))}
          </div>
        )}

        {/* ── Section 1: Aerodynamic parameters ── */}
        <section>
          <h2 className="mb-2 font-[family-name:var(--font-geist-sans)] text-[11px] uppercase tracking-wider text-muted-foreground">
            Aerodynamic Parameters
          </h2>
          <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-card-muted p-4">
            <NumericField
              label="Altitude (m)"
              value={altitude}
              onChange={setAltitude}
              step={100}
              min={0}
              unit="m"
              testId="input-altitude"
            />
            <NumericField
              label="Drag Coefficient (cd0)"
              value={cd0}
              onChange={setCd0}
              step={0.001}
              min={0}
              testId="input-cd0"
            />
            {sRefDisplay != null && (
              <NumericField
                label="Wing Area (m²)"
                value={sRefDisplay}
                onChange={() => undefined}
                step={0.01}
                unit="m²"
                readOnly
                testId="input-sref"
              />
            )}
            <NumericField
              label="Prop Efficiency (η_prop)"
              value={etaProp}
              onChange={setEtaProp}
              step={0.01}
              min={0.1}
              max={1.0}
              testId="input-eta-prop"
            />
            <NumericField
              label="Motor Efficiency (η_motor)"
              value={etaMotor}
              onChange={setEtaMotor}
              step={0.01}
              min={0.1}
              max={1.0}
              testId="input-eta-motor"
            />
          </div>
          <p className="mt-1 font-[family-name:var(--font-geist-sans)] text-[9px] text-subtle-foreground">
            cd0 and wing area from aerodynamic analysis (gh-924). Prop efficiency is a
            placeholder — see prop-finder Phase 2 (#199).
          </p>
        </section>

        {/* ── Section 2: Mission parameters ── */}
        <section>
          <h2 className="mb-2 font-[family-name:var(--font-geist-sans)] text-[11px] uppercase tracking-wider text-muted-foreground">
            Mission Parameters
          </h2>
          <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-card-muted p-4">
            <NumericField
              label="Airframe Mass (kg)"
              value={airframeMass}
              onChange={setAirframeMass}
              step={0.1}
              min={0.1}
              unit="kg"
              testId="input-airframe-mass"
            />
            <NumericField
              label="Cruise Speed (m/s)"
              value={cruiseSpeed}
              onChange={setCruiseSpeed}
              step={0.5}
              min={1}
              unit="m/s"
              testId="input-cruise-speed"
            />
            <NumericField
              label="Top Speed (m/s)"
              value={topSpeed}
              onChange={setTopSpeed}
              step={0.5}
              min={1}
              unit="m/s"
              testId="input-top-speed"
            />
            <NumericField
              label="Flight Time (min)"
              value={flightTime}
              onChange={setFlightTime}
              step={1}
              min={1}
              unit="min"
              testId="input-flight-time"
            />
          </div>
        </section>

        {/* ── Section 3: Motor picker ── */}
        <section>
          <h2 className="mb-2 font-[family-name:var(--font-geist-sans)] text-[11px] uppercase tracking-wider text-muted-foreground">
            Motor Selection (Optional)
          </h2>
          <p className="mb-2 font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Pick a motor to pre-fill its efficiency. The sizing will match compatible
            ESC/battery combos from the catalog.
          </p>
          {/* Motor search */}
          <div className="mb-2 flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-1.5">
            <input
              type="text"
              value={motorSearch}
              onChange={(e) => setMotorSearch(e.target.value)}
              placeholder="Filter motors…"
              className="flex-1 bg-transparent text-[11px] text-foreground outline-none placeholder:text-subtle-foreground"
              data-testid="motor-search"
            />
          </div>
          {/* Motor table */}
          <div
            className="max-h-40 overflow-y-auto rounded-xl border border-border bg-card"
            data-testid="motor-table"
          >
            {filteredMotors.length === 0 && (
              <p className="py-4 text-center font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
                {(defaults?.motors ?? []).length === 0
                  ? "No brushless motors in the component library yet."
                  : "No motors match your filter."}
              </p>
            )}
            {filteredMotors.length > 0 && (
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-border font-[family-name:var(--font-geist-sans)] text-[9px] uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="py-1.5 pr-3 text-left w-4" />
                    <th scope="col" className="py-1.5 pr-3 text-left">Motor</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">Brand</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">KV</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">Max P</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">Eff.</th>
                    <th scope="col" className="py-1.5 text-left">Mass</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMotors.map((m) => (
                    <MotorRow
                      key={m.id}
                      motor={m}
                      isSelected={selectedMotorId === m.id}
                      onSelect={() => handleSelectMotor(m)}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {selectedMotorId != null && (
            <p
              className="mt-1 font-[family-name:var(--font-geist-sans)] text-[9px] text-emerald-400"
              data-testid="motor-selected-notice"
            >
              Motor efficiency pre-filled from specs (η_motor = {etaMotor.toFixed(2)}).
            </p>
          )}
        </section>

        {/* ── Run button ── */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunSizing}
            disabled={sizing}
            className="flex items-center gap-2 rounded-full bg-primary px-5 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
            data-testid="run-sizing-btn"
          >
            {sizing ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Zap size={13} />
            )}
            {sizing ? "Computing…" : "Run Sizing"}
          </button>
          {sizingError && (
            <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-destructive">
              {sizingError}
            </span>
          )}
        </div>

        {/* ── Section 4: Results ── */}
        {candidates.length > 0 && (
          <section data-testid="results-section">
            <h2 className="mb-2 font-[family-name:var(--font-geist-sans)] text-[11px] uppercase tracking-wider text-muted-foreground">
              Motor + Battery Recommendations
            </h2>
            <p className="mb-2 font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
              Sorted by confidence. Select a combination, then click &ldquo;Add to
              Component Tree&rdquo;.
            </p>
            <div className="overflow-x-auto rounded-xl border border-border bg-card">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-border font-[family-name:var(--font-geist-sans)] text-[9px] uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="py-1.5 pr-3 text-left w-4" />
                    <th scope="col" className="py-1.5 pr-3 text-left">Motor</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">ESC</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">Battery</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">Flight Time</th>
                    <th scope="col" className="py-1.5 pr-3 text-left">Cruise Power</th>
                    <th scope="col" className="py-1.5 text-left">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c, idx) => (
                    <CandidateRow
                      key={`${c.motor_id}-${c.battery_id}-${idx}`}
                      candidate={c}
                      isSelected={selectedCandidateIdx === idx}
                      onSelect={() => setSelectedCandidateIdx(idx)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {candidates.length === 0 && !sizing && sizingError == null && initialized && (
          <p
            className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground"
            data-testid="no-candidates-note"
          >
            Click &ldquo;Run Sizing&rdquo; to compute motor/battery recommendations from the
            component library.
          </p>
        )}

        {/* ── Add to tree footer ── */}
        <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
          <div className="flex flex-col gap-0.5">
            {addError && (
              <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-destructive">
                {addError}
              </span>
            )}
            {selectedCandidateIdx != null && candidates[selectedCandidateIdx] && (
              <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                Will add:{" "}
                <span className="text-foreground">
                  {candidates[selectedCandidateIdx].motor_name ?? "motor"}
                </span>
                {candidates[selectedCandidateIdx].esc_id != null && (
                  <>
                    {" "}
                    + <span className="text-foreground">{candidates[selectedCandidateIdx].esc_name ?? "ESC"}</span>
                  </>
                )}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-full border border-border px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Cancel
            </button>
            <button
              onClick={handleAddToTree}
              disabled={selectedCandidateIdx == null || adding}
              className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-40"
              data-testid="add-to-tree-btn"
            >
              {adding ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Check size={12} />
              )}
              Add to Component Tree
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}
