"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, Eye } from "lucide-react";
import { AirfoilSelector } from "./AirfoilSelector";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useUnsavedChanges } from "./UnsavedChangesContext";
import { useWing, type XSec } from "@/hooks/useWings";
import { useWingConfig } from "@/hooks/useWingConfig";
import type { WingConfigSegment } from "@/hooks/useWingConfig";
import { useFuselage, type FuselageXSec } from "@/hooks/useFuselage";
import { ImportFuselageDialog } from "./ImportFuselageDialog";
import { Box } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";

/** Parse a number input string, allowing empty/partial input during editing */
function num(v: string, fallback = 0): number {
  if (v === "" || v === "-" || v === ".") return fallback;
  const n = parseFloat(v);
  return isNaN(n) ? fallback : n;
}

// ── Types ───────────────────────────────────────────────────────

type Mode = "wingconfig" | "asb" | "fuselage";

interface WingConfigState {
  root_airfoil: string;
  root_chord: number;       // mm
  root_dihedral: number;    // degrees
  root_incidence: number;   // degrees
  root_rotation_point: number;
  tip_airfoil: string;
  tip_chord: number;        // mm
  tip_dihedral: number;
  tip_incidence: number;
  tip_rotation_point: number;
  length: number;           // mm
  sweep: number;            // mm
  number_interpolation_points: number;
  tip_type: string;
}

interface AsbState {
  airfoil: string;
  chord: number;            // display in mm (stored in m)
  twist: number;            // degrees
  xyz_le: [number, number, number]; // meters
}

// ── Converters ──────────────────────────────────────────────────

function xsecToAsb(xsec: XSec): AsbState {
  return {
    airfoil: airfoilShortName(xsec.airfoil),
    chord: xsec.chord * 1000,
    twist: xsec.twist,
    xyz_le: [xsec.xyz_le[0], xsec.xyz_le[1], xsec.xyz_le[2]],
  };
}

function asbToPayload(asb: AsbState): Partial<XSec> {
  return {
    airfoil: asb.airfoil,
    chord: asb.chord / 1000,
    twist: asb.twist,
    xyz_le: [...asb.xyz_le],
  };
}

/** Extract short airfoil name from path like "./components/airfoils/mh32.dat" → "mh32" */
function airfoilShortName(raw: string): string {
  const basename = raw.split("/").pop() ?? raw;
  return basename.replace(/\.dat$/i, "");
}

function segmentToWcState(seg: WingConfigSegment): WingConfigState {
  return {
    root_airfoil: airfoilShortName(seg.root_airfoil.airfoil),
    root_chord: seg.root_airfoil.chord,
    root_dihedral: seg.root_airfoil.dihedral_as_rotation_in_degrees ?? 0,
    root_incidence: seg.root_airfoil.incidence ?? 0,
    root_rotation_point: seg.root_airfoil.rotation_point_rel_chord ?? 0.25,
    tip_airfoil: airfoilShortName(seg.tip_airfoil.airfoil),
    tip_chord: seg.tip_airfoil.chord,
    tip_dihedral: seg.tip_airfoil.dihedral_as_rotation_in_degrees ?? 0,
    tip_incidence: seg.tip_airfoil.incidence ?? 0,
    tip_rotation_point: seg.tip_airfoil.rotation_point_rel_chord ?? 0.25,
    length: seg.length,
    sweep: seg.sweep,
    number_interpolation_points: seg.number_interpolation_points ?? 201,
    tip_type: seg.tip_type ?? "",
  };
}

/** @deprecated — kept for reference, replaced by segmentToWcState + useWingConfig */
function xsecsToWingConfig(
  xsecs: XSec[],
  segIndex: number,
): WingConfigState | null {
  if (segIndex < 0 || segIndex >= xsecs.length - 1) return null;
  const root = xsecs[segIndex];
  const tip = xsecs[segIndex + 1];
  const rootChord = root.chord * 1000;
  const tipChord = tip.chord * 1000;
  const dx = (tip.xyz_le[0] - root.xyz_le[0]) * 1000;
  const dy = (tip.xyz_le[1] - root.xyz_le[1]) * 1000;

  // Estimate dihedral from z-component of leading-edge delta
  const segLength = Math.sqrt(dx * dx + dy * dy);
  const dz = (tip.xyz_le[2] - root.xyz_le[2]) * 1000;
  const dihedralDeg = segLength > 0 ? Math.atan2(dz, Math.abs(dy)) * (180 / Math.PI) : 0;

  return {
    root_airfoil: airfoilShortName(root.airfoil),
    root_chord: rootChord,
    root_dihedral: Math.round(dihedralDeg * 100) / 100,
    root_incidence: root.twist,
    root_rotation_point: 0.25,
    tip_airfoil: airfoilShortName(tip.airfoil),
    tip_chord: tipChord,
    tip_dihedral: Math.round(dihedralDeg * 100) / 100,
    tip_incidence: tip.twist,
    tip_rotation_point: 0.25,
    length: Math.abs(dy),
    sweep: dx,
    number_interpolation_points: root.number_interpolation_points ?? 201,
    tip_type: root.tip_type ?? "",
  };
}

// ── Field Component ─────────────────────────────────────────────

function Field({
  label,
  value,
  suffix,
  type = "number",
  onChange,
  readOnly,
  isSelect,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  type?: "text" | "number";
  onChange?: (v: string) => void;
  readOnly?: boolean;
  isSelect?: boolean;
}) {
  const [localValue, setLocalValue] = useState(String(value));
  const [editing, setEditing] = useState(false);

  // Sync from parent when not actively editing
  useEffect(() => {
    if (!editing) setLocalValue(String(value));
  }, [value, editing]);

  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        {readOnly ? (
          <span className="text-[13px] text-foreground">{value}</span>
        ) : (
          <input
            type={type}
            step="any"
            value={editing ? localValue : String(value)}
            onFocus={() => setEditing(true)}
            onChange={(e) => {
              setLocalValue(e.target.value);
              onChange?.(e.target.value);
            }}
            onBlur={() => {
              setEditing(false);
            }}
            className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
        )}
        <span className="flex-shrink-0">
          {isSelect && (
            <ChevronDown size={12} className="text-muted-foreground" />
          )}
          {suffix && (
            <span className="text-[11px] text-muted-foreground">{suffix}</span>
          )}
        </span>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────

export function PropertyForm({ onGeometryChanged }: { onGeometryChanged?: (wingName: string) => void }) {
  const { aeroplaneId, selectedWing, selectedXsecIndex, selectedFuselage, selectedFuselageXsecIndex, treeMode } =
    useAeroplaneContext();
  const { wing, updateXSec, mutate } = useWing(aeroplaneId, selectedWing);
  const { wingConfig, saveWingConfig, mutate: mutateWc } = useWingConfig(
    aeroplaneId,
    treeMode === "wingconfig" ? selectedWing : null,
  );
  const { fuselage, updateXSec: updateFuselageXSec, mutate: mutateFuselage } = useFuselage(
    aeroplaneId,
    treeMode === "fuselage" ? selectedFuselage : null,
  );

  const { setDirty } = useUnsavedChanges();
  const router = useRouter();

  // (TED editing is now handled by TedEditDialog — no more tedSaveRef needed)

  // Mode is driven by tree toggle, not local state
  const mode: Mode = treeMode;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ASB state
  const xsec =
    wing && selectedXsecIndex !== null
      ? wing.x_secs[selectedXsecIndex] ?? null
      : null;
  const [asb, setAsb] = useState<AsbState | null>(null);

  // WingConfig state — loaded from the backend /wingconfig endpoint
  const [wc, setWc] = useState<WingConfigState | null>(null);

  // Sync ASB state when selection changes
  useEffect(() => {
    if (xsec) {
      setAsb(xsecToAsb(xsec));
    } else {
      setAsb(null);
    }
    setError(null);
  }, [xsec?.airfoil, xsec?.chord, xsec?.twist, xsec?.xyz_le?.[0], xsec?.xyz_le?.[1], xsec?.xyz_le?.[2], selectedXsecIndex]);

  // Sync WingConfig state from API response
  // nose_pnt state (mm) — only editable on segment 0
  const [nosePnt, setNosePnt] = useState<[number, number, number]>([0, 0, 0]);

  useEffect(() => {
    if (wingConfig && selectedXsecIndex !== null && selectedXsecIndex < wingConfig.segments.length) {
      const seg = wingConfig.segments[selectedXsecIndex];
      setWc(segmentToWcState(seg));
    } else {
      setWc(null);
    }
    if (wingConfig?.nose_pnt) {
      setNosePnt(wingConfig.nose_pnt.map((v) => v * 1000) as [number, number, number]);
    }
  }, [wingConfig, selectedXsecIndex]);

  // Fuselage xsec mode
  if (mode === "fuselage" && selectedFuselage && selectedFuselageXsecIndex !== null && fuselage) {
    const fxsec = fuselage.x_secs[selectedFuselageXsecIndex];
    if (fxsec) {
      return (
        <FuselageXSecForm
          aeroplaneId={aeroplaneId}
          fuselageName={selectedFuselage}
          xsecIndex={selectedFuselageXsecIndex}
          xsec={fxsec}
          onSave={async (updated) => {
            await updateFuselageXSec(selectedFuselageXsecIndex, updated);
          }}
        />
      );
    }
  }

  // No segment/xsec selected — nothing to show
  if (selectedXsecIndex === null || !xsec) {
    return null;
  }

  function handleCancel() {
    if (xsec) setAsb(xsecToAsb(xsec));
    if (wing && selectedXsecIndex !== null)
      setWc(xsecsToWingConfig(wing.x_secs, selectedXsecIndex));
    setError(null);
    setDirty(false);
  }

  async function handleSaveAsb() {
    if (!asb) return;
    setSaving(true);
    setError(null);
    try {
      await updateXSec(selectedXsecIndex!, asbToPayload(asb));
      await mutate();
      if (selectedWing) onGeometryChanged?.(selectedWing);
      setDirty(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveWingConfig() {
    if (!wc || !wingConfig || selectedXsecIndex === null) return;
    setSaving(true);
    setError(null);
    try {
      // Build updated WingConfig: replace the edited segment, keep others
      const updatedSegments = wingConfig.segments.map((seg, i) => {
        if (i !== selectedXsecIndex) return seg;
        return {
          ...seg,
          root_airfoil: {
            airfoil: wc.root_airfoil,
            chord: wc.root_chord,
            dihedral_as_rotation_in_degrees: wc.root_dihedral,
            incidence: wc.root_incidence,
            rotation_point_rel_chord: wc.root_rotation_point,
          },
          tip_airfoil: {
            airfoil: wc.tip_airfoil,
            chord: wc.tip_chord,
            dihedral_as_rotation_in_degrees: wc.tip_dihedral,
            incidence: wc.tip_incidence,
            rotation_point_rel_chord: wc.tip_rotation_point,
          },
          length: wc.length,
          sweep: wc.sweep,
          number_interpolation_points: wc.number_interpolation_points,
          tip_type: wc.tip_type || undefined,
        };
      });

      await saveWingConfig({
        ...wingConfig,
        nose_pnt: nosePnt.map((v) => v / 1000),
        segments: updatedSegments,
      });
      await mutate();
      await mutateWc();
      if (selectedWing) onGeometryChanged?.(selectedWing);
      setDirty(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const handleSave = mode === "wingconfig" ? handleSaveWingConfig : handleSaveAsb;

  return (
    <div className="rounded-xl border border-border bg-card p-2.5 px-4">
      {/* Header */}
      <div className="mb-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {mode === "wingconfig" ? `segment ${selectedXsecIndex}` : `x_sec ${selectedXsecIndex}`} &middot; Properties
        </span>
      </div>

      {/* Field grid */}
      <div className="flex flex-col gap-3">
        {mode === "wingconfig" && wc ? (
          <>
            {/* Wing-level: symmetric + nose_pnt — only on segment 0 */}
            {selectedXsecIndex === 0 && (
              <>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={wingConfig?.symmetric ?? true}
                    onChange={(e) => {
                      setDirty(true);
                      if (wingConfig) wingConfig.symmetric = e.target.checked;
                      // Force re-render via state toggle
                      setWc({ ...wc });
                    }}
                    className="h-4 w-4"
                  />
                  <span className="text-[11px] text-muted-foreground">symmetric wing</span>
                </div>
                <div className="flex gap-3">
                  <Field label="nose x" value={nosePnt[0]} suffix="mm"
                    onChange={(v) => { setDirty(true); setNosePnt([num(v), nosePnt[1], nosePnt[2]]); }} />
                  <Field label="nose y" value={nosePnt[1]} suffix="mm"
                    onChange={(v) => { setDirty(true); setNosePnt([nosePnt[0], num(v), nosePnt[2]]); }} />
                  <Field label="nose z" value={nosePnt[2]} suffix="mm"
                    onChange={(v) => { setDirty(true); setNosePnt([nosePnt[0], nosePnt[1], num(v)]); }} />
                </div>
              </>
            )}
            {/* Row 1: root_airfoil | tip_airfoil */}
            <div className="flex gap-3">
              <div className="flex flex-1 items-end gap-1.5">
                <div className="flex-1">
                  <AirfoilSelector
                    label="root_airfoil"
                    value={wc.root_airfoil}
                    onChange={(v) => { setDirty(true); setWc({ ...wc, root_airfoil: v }); }}
                  />
                </div>
                <button
                  onClick={() => router.push("/workbench/airfoil-preview")}
                  className="mb-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
                  title="Preview airfoil"
                >
                  <Eye size={14} />
                </button>
              </div>
              <div className="flex flex-1 items-end gap-1.5">
                <div className="flex-1">
                  <AirfoilSelector
                    label="tip_airfoil"
                    value={wc.tip_airfoil}
                    onChange={(v) => { setDirty(true); setWc({ ...wc, tip_airfoil: v }); }}
                  />
                </div>
                <button
                  onClick={() => router.push("/workbench/airfoil-preview")}
                  className="mb-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
                  title="Preview airfoil"
                >
                  <Eye size={14} />
                </button>
              </div>
            </div>
            {/* Row 2: root_chord | tip_chord */}
            <div className="flex gap-3">
              <Field
                label="root_chord"
                value={wc.root_chord}
                suffix="mm"
                onChange={(v) => { setDirty(true); setWc({ ...wc, root_chord: num(v) }); }}
              />
              <Field
                label="tip_chord"
                value={wc.tip_chord}
                suffix="mm"
                onChange={(v) => { setDirty(true); setWc({ ...wc, tip_chord: num(v) }); }}
              />
            </div>
            {/* Row 3: length | sweep */}
            <div className="flex gap-3">
              <Field
                label="length"
                value={wc.length}
                suffix="mm"
                onChange={(v) => { setDirty(true); setWc({ ...wc, length: num(v) }); }}
              />
              <Field
                label="sweep"
                value={wc.sweep}
                suffix="mm"
                onChange={(v) => { setDirty(true); setWc({ ...wc, sweep: num(v) }); }}
              />
            </div>
            {/* Row 4: dihedral | incidence */}
            <div className="flex gap-3">
              <Field
                label="dihedral"
                value={wc.root_dihedral}
                suffix="°"
                onChange={(v) => { setDirty(true); setWc({ ...wc, root_dihedral: num(v) }); }}
              />
              <Field
                label="incidence"
                value={wc.root_incidence}
                suffix="°"
                onChange={(v) => { setDirty(true); setWc({ ...wc, root_incidence: num(v) }); }}
              />
            </div>
            {/* Row 5: rotation_point | interpolation_pts */}
            <div className="flex gap-3">
              <Field
                label="rotation_point"
                value={wc.root_rotation_point}
                onChange={(v) => { setDirty(true); setWc({ ...wc, root_rotation_point: num(v, 0.25) }); }}
              />
              <Field
                label="interpolation_pts"
                value={wc.number_interpolation_points}
                onChange={(v) => { setDirty(true); setWc({ ...wc, number_interpolation_points: num(v, 201) }); }}
              />
            </div>
            {/* Row 6: tip_type */}
            <div className="flex gap-3">
              <div className="flex flex-1 flex-col gap-1">
                <label className="text-[11px] text-muted-foreground">tip_type</label>
                <select
                  value={wc.tip_type}
                  onChange={(e) => { setDirty(true); setWc({ ...wc, tip_type: e.target.value }); }}
                  className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                >
                  <option value="">none</option>
                  <option value="flat">flat</option>
                  <option value="round">round</option>
                </select>
              </div>
              <div className="flex-1" />
            </div>
            {/* Tip airfoil overrides (collapsible) */}
            <TipOverrideSection wc={wc} setWc={setWc} setDirty={setDirty} />
          </>
        ) : asb ? (
          <>
            {/* ASB mode: airfoil | chord */}
            <div className="flex gap-3">
              <AirfoilSelector
                label="airfoil"
                value={asb.airfoil}
                onChange={(v) => { setDirty(true); setAsb({ ...asb, airfoil: v }); }}
              />
              <Field
                label="chord"
                value={asb.chord}
                suffix="mm"
                onChange={(v) => { setDirty(true); setAsb({ ...asb, chord: num(v) }); }}
              />
            </div>
            {/* twist | x_sec_type */}
            <div className="flex gap-3">
              <Field
                label="twist"
                value={asb.twist}
                suffix="°"
                onChange={(v) => { setDirty(true); setAsb({ ...asb, twist: num(v) }); }}
              />
              <Field
                label="x_sec_type"
                value={xsec.x_sec_type ?? "\u2014"}
                readOnly
              />
            </div>
            {/* xyz_le */}
            <div className="flex gap-3">
              {(["x", "y", "z"] as const).map((axis, i) => (
                <Field
                  key={axis}
                  label={`xyz_le.${axis}`}
                  value={asb.xyz_le[i]}
                  suffix="m"
                  onChange={(v) => {
                    setDirty(true);
                    const next: [number, number, number] = [...asb.xyz_le];
                    next[i] = num(v);
                    setAsb({ ...asb, xyz_le: next });
                  }}
                />
              ))}
            </div>
          </>
        ) : (
          <p className="py-4 text-center text-[12px] text-muted-foreground">
            {mode === "wingconfig"
              ? "Last segment has no WingConfig view (terminal x_sec)"
              : "No data available"}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col items-end gap-2 pt-4">
        <div className="flex gap-2">
          <button
            onClick={handleCancel}
            disabled={saving}
            className="rounded-full border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving\u2026" : "Save"}
          </button>
        </div>
        {error && <p className="text-[12px] text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// ── Tip Override Section ────────────────────────────────────────

function TipOverrideSection({
  wc,
  setWc,
  setDirty,
}: {
  wc: WingConfigState;
  setWc: (wc: WingConfigState) => void;
  setDirty: (dirty: boolean) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-1 border-t border-border pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Tip Airfoil Overrides
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="flex gap-3">
            <Field
              label="tip_dihedral"
              value={wc.tip_dihedral}
              suffix="°"
              onChange={(v) => { setDirty(true); setWc({ ...wc, tip_dihedral: num(v) }); }}
            />
            <Field
              label="tip_incidence"
              value={wc.tip_incidence}
              suffix="°"
              onChange={(v) => { setDirty(true); setWc({ ...wc, tip_incidence: num(v) }); }}
            />
          </div>
          <div className="flex gap-3">
            <Field
              label="tip_rotation_point"
              value={wc.tip_rotation_point}
              onChange={(v) => { setDirty(true); setWc({ ...wc, tip_rotation_point: num(v, 0.25) }); }}
            />
            <div className="flex-1" />
          </div>
        </div>
      )}
    </div>
  );
}


// ── Fuselage XSec Form ────────────────────────────────────────

function FuselageXSecForm({
  aeroplaneId,
  fuselageName,
  xsecIndex,
  xsec,
  onSave,
}: {
  aeroplaneId: string | null;
  fuselageName: string;
  xsecIndex: number;
  xsec: FuselageXSec;
  onSave: (updated: FuselageXSec) => Promise<void>;
}) {
  const [xyz0, setXyz0] = useState(String(xsec.xyz[0]));
  const [xyz1, setXyz1] = useState(String(xsec.xyz[1]));
  const [xyz2, setXyz2] = useState(String(xsec.xyz[2]));
  const [a, setA] = useState(String(xsec.a));
  const [b, setB] = useState(String(xsec.b));
  const [n, setN] = useState(String(xsec.n));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [show3DEditor, setShow3DEditor] = useState(false);
  const { setDirty } = useUnsavedChanges();

  // Get full fuselage data for 3D editor
  const { fuselage, mutate: mutateFuselage } = useFuselage(aeroplaneId, fuselageName);

  useEffect(() => {
    setXyz0(String(xsec.xyz[0]));
    setXyz1(String(xsec.xyz[1]));
    setXyz2(String(xsec.xyz[2]));
    setA(String(xsec.a));
    setB(String(xsec.b));
    setN(String(xsec.n));
    setError(null);
  }, [xsec, xsecIndex]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave({
        xyz: [parseFloat(xyz0) || 0, parseFloat(xyz1) || 0, parseFloat(xyz2) || 0],
        a: parseFloat(a) || 0.001,
        b: parseFloat(b) || 0.001,
        n: Math.max(0.5, Math.min(10, parseFloat(n) || 2)),
      });
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setXyz0(String(xsec.xyz[0]));
    setXyz1(String(xsec.xyz[1]));
    setXyz2(String(xsec.xyz[2]));
    setA(String(xsec.a));
    setB(String(xsec.b));
    setN(String(xsec.n));
    setDirty(false);
  };

  const markDirty = () => setDirty(true);

  return (
    <div className="rounded-xl border border-border bg-card p-2.5 px-4">
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {fuselageName} {"\u00B7"} xsec {xsecIndex} Properties
        </span>
        <span className="flex-1" />
        <button
          onClick={() => setShow3DEditor(true)}
          className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-[11px] text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title="Edit in 3D viewer"
        >
          <Box size={12} />
          3D Edit
        </button>
      </div>

      {show3DEditor && fuselage && (
        <ImportFuselageDialog
          open={show3DEditor}
          onClose={() => { setShow3DEditor(false); mutateFuselage(); }}
          aeroplaneId={aeroplaneId}
          onSaved={() => { setShow3DEditor(false); mutateFuselage(); }}
          initialXsecs={fuselage.x_secs}
          initialName={fuselageName}
          initialSelectedIndex={xsecIndex}
        />
      )}

      <div className="mt-3 flex flex-col gap-3">
        <div className="flex gap-3">
          <Field label="xyz[x]" value={xyz0} suffix="m" onChange={(v) => { setXyz0(v); markDirty(); }} />
          <Field label="xyz[y]" value={xyz1} suffix="m" onChange={(v) => { setXyz1(v); markDirty(); }} />
          <Field label="xyz[z]" value={xyz2} suffix="m" onChange={(v) => { setXyz2(v); markDirty(); }} />
        </div>
        <div className="flex gap-3">
          <Field label="a (semi-width)" value={a} suffix="m" onChange={(v) => { setA(v); markDirty(); }} />
          <Field label="b (semi-height)" value={b} suffix="m" onChange={(v) => { setB(v); markDirty(); }} />
        </div>
        <div className="flex gap-3">
          <Field label="n (exponent)" value={n} onChange={(v) => { setN(v); markDirty(); }} />
        </div>
      </div>

      {error && (
        <p className="mt-2 rounded-xl border border-destructive bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
          {error}
        </p>
      )}

      <div className="mt-3 flex justify-end gap-2">
        <button onClick={handleCancel} disabled={saving}
          className="rounded-full border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50">
          Cancel
        </button>
        <button onClick={handleSave} disabled={saving}
          className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50">
          {saving ? "Saving\u2026" : "Save"}
        </button>
      </div>
    </div>
  );
}
