"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ChevronDown, ChevronRight, ChevronUp, Eye, Search } from "lucide-react";
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
import { useComponents, type Component } from "@/hooks/useComponents";

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
              // For text fields, propagate immediately
              if (type === "text") onChange?.(e.target.value);
            }}
            onBlur={() => {
              setEditing(false);
              if (type !== "text") onChange?.(localValue);
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

  // No segment/xsec selected — show placeholder
  if (selectedXsecIndex === null || !xsec) {
    const msg = mode === "fuselage"
      ? "Select a cross-section in the tree"
      : "Select a segment in the tree";
    return (
      <div className="rounded-xl border border-border bg-card p-4">
        <p className="py-2 text-center text-[12px] text-muted-foreground">{msg}</p>
      </div>
    );
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

      {/* Trailing Edge Device section */}
      <TedSection
        aeroplaneId={aeroplaneId}
        wingName={selectedWing}
        xsecIndex={selectedXsecIndex!}
        ted={xsec.trailing_edge_device}
        onSaved={() => mutate()}
      />

      {/* Spars section */}
      <SparsSection
        aeroplaneId={aeroplaneId}
        wingName={selectedWing}
        xsecIndex={selectedXsecIndex!}
        spars={xsec.spare_list ?? []}
        onSaved={() => mutate()}
      />

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


// ── Servo Picker (gh#99) ────────────────────────────────────────

/** Maps a Component's specs to the Servo CAD object expected by the API.
 *  Includes component_id so the backend can link back to the library entry. */
function componentToServoPayload(comp: Component): Record<string, unknown> {
  const s = comp.specs;
  return {
    component_id: comp.id,
    length: Number(s.servo_length ?? 0),
    width: Number(s.servo_width ?? 0),
    height: Number(s.servo_height ?? 0),
    leading_length: Number(s.leading_length ?? 0),
    latch_z: Number(s.latch_z ?? 0),
    latch_x: Number(s.latch_x ?? 0),
    latch_thickness: Number(s.latch_thickness ?? 0),
    latch_length: Number(s.latch_length ?? 0),
    cable_z: Number(s.cable_z ?? 0),
    screw_hole_lx: Number(s.screw_hole_lx ?? 0),
    screw_hole_d: Number(s.screw_hole_d ?? 0),
  };
}

function ServoPickerInline({
  aeroplaneId,
  wingName,
  xsecIndex,
  ted,
  onAssigned,
}: {
  aeroplaneId: string | null;
  wingName: string | null;
  xsecIndex: number;
  ted: Record<string, unknown> | null | undefined;
  onAssigned: () => void;
}) {
  const { components: servos } = useComponents("servo");

  // Resolve the currently assigned servo name via component_id in the TED's servo data
  const servoData = ted && typeof ted === "object"
    ? (ted as Record<string, unknown>).servo as Record<string, unknown> | null | undefined
    : null;
  const assignedComponentId = servoData && typeof servoData === "object"
    ? (servoData as Record<string, unknown>).component_id as number | null | undefined
    : null;
  const currentServoName = assignedComponentId
    ? servos.find((s) => s.id === assignedComponentId)?.name ?? `Servo #${assignedComponentId}`
    : servoData ? "Servo (unknown)" : null;
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [assigning, setAssigning] = useState(false);
  const [servoError, setServoError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const list = q ? servos.filter((s) => s.name.toLowerCase().includes(q)) : servos;
    return list.slice(0, 20);
  }, [servos, search]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Auto-focus search on open
  useEffect(() => {
    if (open) searchRef.current?.focus();
  }, [open]);

  function toggle() {
    setOpen((v) => !v);
    if (open) setSearch("");
  }

  async function assignServo(comp: Component) {
    if (!aeroplaneId || !wingName) {
      setServoError("No aeroplane/wing selected");
      return;
    }
    setAssigning(true);
    setServoError(null);
    try {
      const payload = componentToServoPayload(comp);
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface/cad_details/servo_details`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ servo: payload }),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${text}`);
      }
      setOpen(false);
      setSearch("");
      onAssigned();
    } catch (err) {
      setServoError(err instanceof Error ? err.message : String(err));
    } finally {
      setAssigning(false);
    }
  }

  async function removeServo() {
    if (!aeroplaneId || !wingName) return;
    setAssigning(true);
    setServoError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface/cad_details/servo_details`,
        { method: "DELETE" },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${text}`);
      }
      setOpen(false);
      setSearch("");
      onAssigned();
    } catch (err) {
      setServoError(err instanceof Error ? err.message : String(err));
    } finally {
      setAssigning(false);
    }
  }

  return (
    <div ref={containerRef} className={`relative flex flex-col gap-1 ${open ? "z-[100]" : ""}`}>
      <label className="text-[11px] text-muted-foreground">Servo</label>

      {/* Trigger button */}
      <button
        onClick={toggle}
        disabled={assigning}
        className={`flex items-center gap-2 rounded-xl px-3 py-2 transition-colors ${
          open ? "border-2 border-primary bg-input" : "border border-border bg-input"
        } disabled:opacity-50`}
      >
        <span className="text-[13px] text-foreground">
          {currentServoName || "None"}
        </span>
        <div className="flex-1" />
        {open ? (
          <ChevronUp size={12} className="text-primary" />
        ) : (
          <ChevronDown size={12} className="text-muted-foreground" />
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full z-50 mt-1 w-full rounded-xl border border-border bg-card shadow-lg">
          {/* Search */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search size={13} className="text-muted-foreground" />
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search servos…"
              className="flex-1 bg-transparent text-[13px] text-foreground placeholder:text-subtle-foreground outline-none"
            />
          </div>

          {/* List */}
          <div className="max-h-[200px] overflow-y-auto py-1">
            {/* None option — always first */}
            <button
              onClick={removeServo}
              disabled={assigning}
              className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-sidebar-accent disabled:opacity-50"
            >
              {!currentServoName ? (
                <Check size={12} className="text-primary" />
              ) : (
                <div className="w-3" />
              )}
              <span className="text-[13px] text-muted-foreground italic">None</span>
            </button>

            {filtered.length === 0 && (
              <div className="px-3 py-3 text-center text-[12px] text-muted-foreground">
                No servos found
              </div>
            )}
            {filtered.map((s) => (
              <button
                key={s.id}
                onClick={() => assignServo(s)}
                disabled={assigning}
                className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-sidebar-accent disabled:opacity-50"
              >
                {s.name === currentServoName ? (
                  <Check size={12} className="text-primary" />
                ) : (
                  <div className="w-3" />
                )}
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                  {s.name}
                </span>
                {s.manufacturer && (
                  <span className="text-[12px] text-muted-foreground">
                    ({s.manufacturer})
                  </span>
                )}
                {s.mass_g != null && (
                  <>
                    <span className="flex-1" />
                    <span className="text-[10px] text-subtle-foreground">{s.mass_g}g</span>
                  </>
                )}
              </button>
            ))}
          </div>

          {servos.length > 20 && !search && (
            <div className="border-t border-border px-3 py-2 text-center">
              <span className="text-[11px] text-subtle-foreground">
                {servos.length - 20} more — type to narrow
              </span>
            </div>
          )}
        </div>
      )}
      {servoError && (
        <p className="mt-1 text-[11px] text-red-500">{servoError}</p>
      )}
    </div>
  );
}


// ── TED Section ─────────────────────────────────────────────────

const HINGE_TYPES = ["middle", "top", "top_simple", "round_inside", "round_outside"] as const;

function TedSection({
  aeroplaneId,
  wingName,
  xsecIndex,
  ted,
  onSaved,
}: {
  aeroplaneId: string | null;
  wingName: string | null;
  xsecIndex: number;
  ted: Record<string, unknown> | null | undefined;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tedError, setTedError] = useState<string | null>(null);
  // Core fields
  const [name, setName] = useState("");
  const [hingePoint, setHingePoint] = useState("0.8");
  const [symmetric, setSymmetric] = useState(false);
  const [relChordTip, setRelChordTip] = useState("0.8");
  // Deflection
  const [posDeg, setPosDeg] = useState("35");
  const [negDeg, setNegDeg] = useState("35");
  // Spacing / geometry (gh#95)
  const [hingeSpacing, setHingeSpacing] = useState("");
  const [sideSpacingRoot, setSideSpacingRoot] = useState("");
  const [sideSpacingTip, setSideSpacingTip] = useState("");
  const [teOffsetFactor, setTeOffsetFactor] = useState("1.0");
  const [hingeType, setHingeType] = useState("top");
  // Servo (gh#95)
  const [servoPlacement, setServoPlacement] = useState("top");
  const [servoChordPos, setServoChordPos] = useState("");
  const [servoLengthPos, setServoLengthPos] = useState("");

  // Sync from existing TED
  useEffect(() => {
    if (ted && typeof ted === "object") {
      const t = ted as Record<string, unknown>;
      if (t.name) setName(String(t.name));
      if (t.hinge_point) setHingePoint(String(t.hinge_point));
      if (t.symmetric !== undefined) setSymmetric(Boolean(t.symmetric));
      if (t.rel_chord_tip != null) setRelChordTip(String(t.rel_chord_tip));
      if (t.positive_deflection_deg != null) setPosDeg(String(t.positive_deflection_deg));
      if (t.negative_deflection_deg != null) setNegDeg(String(t.negative_deflection_deg));
      if (t.hinge_spacing != null) setHingeSpacing(String(t.hinge_spacing));
      if (t.side_spacing_root != null) setSideSpacingRoot(String(t.side_spacing_root));
      if (t.side_spacing_tip != null) setSideSpacingTip(String(t.side_spacing_tip));
      if (t.trailing_edge_offset_factor != null) setTeOffsetFactor(String(t.trailing_edge_offset_factor));
      if (t.hinge_type) setHingeType(String(t.hinge_type));
      if (t.servo_placement) setServoPlacement(String(t.servo_placement));
      if (t.rel_chord_servo_position != null) setServoChordPos(String(t.rel_chord_servo_position));
      if (t.rel_length_servo_position != null) setServoLengthPos(String(t.rel_length_servo_position));
    }
  }, [ted]);

  const hasTed = ted && typeof ted === "object" && Object.keys(ted).length > 0;

  function optFloat(v: string): number | undefined {
    const trimmed = v.trim();
    if (!trimmed) return undefined;
    const n = parseFloat(trimmed);
    return Number.isFinite(n) ? n : undefined;
  }

  async function handleSaveTed() {
    if (!aeroplaneId || !wingName) return;
    setSaving(true);
    setTedError(null);
    try {
      // PATCH control surface (core ASB fields)
      const csRes = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            hinge_point: parseFloat(hingePoint),
            symmetric,
            deflection: 0,
          }),
        },
      );
      if (!csRes.ok) throw new Error(`Control surface: ${csRes.status}`);

      // PATCH cad details (all geometry + servo positioning)
      const cadPayload: Record<string, unknown> = {
        rel_chord_tip: parseFloat(relChordTip),
        servo_placement: servoPlacement,
        positive_deflection_deg: parseFloat(posDeg),
        negative_deflection_deg: parseFloat(negDeg),
        trailing_edge_offset_factor: optFloat(teOffsetFactor),
        hinge_type: hingeType,
      };
      const hs = optFloat(hingeSpacing);
      if (hs !== undefined) cadPayload.hinge_spacing = hs;
      const ssr = optFloat(sideSpacingRoot);
      if (ssr !== undefined) cadPayload.side_spacing_root = ssr;
      const sst = optFloat(sideSpacingTip);
      if (sst !== undefined) cadPayload.side_spacing_tip = sst;
      const scp = optFloat(servoChordPos);
      if (scp !== undefined) cadPayload.rel_chord_servo_position = scp;
      const slp = optFloat(servoLengthPos);
      if (slp !== undefined) cadPayload.rel_length_servo_position = slp;

      const cadRes = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface/cad_details`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cadPayload),
        },
      );
      if (!cadRes.ok) throw new Error(`CAD details: ${cadRes.status}`);

      onSaved();
    } catch (err: unknown) {
      setTedError(err instanceof Error ? err.message : "TED save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 border-t border-border pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Trailing Edge Device {hasTed ? `(${(ted as Record<string, unknown>).name ?? "set"})` : "(none)"}
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          {/* Core fields */}
          <div className="flex gap-3">
            <Field label="name" value={name} type="text" onChange={setName} />
            <Field label="hinge_point" value={hingePoint} onChange={setHingePoint} />
          </div>
          <div className="flex gap-3">
            <Field label="rel_chord_tip" value={relChordTip} onChange={setRelChordTip} />
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">hinge_type</label>
              <select
                value={hingeType}
                onChange={(e) => setHingeType(e.target.value)}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                {HINGE_TYPES.map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
            </div>
          </div>
          {/* Deflection */}
          <div className="flex gap-3">
            <Field label="positive_deflection_deg" value={posDeg} suffix="°" onChange={setPosDeg} />
            <Field label="negative_deflection_deg" value={negDeg} suffix="°" onChange={setNegDeg} />
          </div>
          {/* Spacing / geometry */}
          <div className="flex gap-3">
            <Field label="hinge_spacing" value={hingeSpacing} suffix="mm" onChange={setHingeSpacing} />
            <Field label="TE_offset_factor" value={teOffsetFactor} onChange={setTeOffsetFactor} />
          </div>
          <div className="flex gap-3">
            <Field label="side_spacing_root" value={sideSpacingRoot} suffix="mm" onChange={setSideSpacingRoot} />
            <Field label="side_spacing_tip" value={sideSpacingTip} suffix="mm" onChange={setSideSpacingTip} />
          </div>
          {/* Servo assignment from component library (gh#99) —
              only available after the TED has been saved at least once */}
          {hasTed ? (
            <ServoPickerInline
              aeroplaneId={aeroplaneId}
              wingName={wingName}
              xsecIndex={xsecIndex}
              ted={ted}
              onAssigned={onSaved}
            />
          ) : (
            <p className="text-[11px] text-muted-foreground italic">
              Save the TED first to assign a servo.
            </p>
          )}
          {/* Servo positioning */}
          <div className="flex gap-3">
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">servo_placement</label>
              <select
                value={servoPlacement}
                onChange={(e) => setServoPlacement(e.target.value)}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                <option value="top">top</option>
                <option value="bottom">bottom</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">servo_chord_pos</label>
              <input
                type="number" min="0" max="1" step="0.01"
                value={servoChordPos}
                onChange={(e) => setServoChordPos(e.target.value)}
                placeholder="0.0 – 1.0"
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
            </div>
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">servo_length_pos</label>
              <input
                type="number" min="0" max="1" step="0.01"
                value={servoLengthPos}
                onChange={(e) => setServoLengthPos(e.target.value)}
                placeholder="0.0 – 1.0"
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
            </div>
          </div>
          {/* Symmetric checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={symmetric}
              onChange={(e) => setSymmetric(e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-[11px] text-muted-foreground">symmetric</span>
          </div>
          <button
            onClick={handleSaveTed}
            disabled={saving || !name}
            className="self-end rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save TED"}
          </button>
          {tedError && <p className="text-[11px] text-red-500">{tedError}</p>}
        </div>
      )}
    </div>
  );
}

// ── Spars Section ───────────────────────────────────────────────

const SPAR_MODES = ["standard", "follow", "normal", "standard_backward", "orthogonal_backward"] as const;

function SparsSection({
  aeroplaneId,
  wingName,
  xsecIndex,
  spars,
  onSaved,
}: {
  aeroplaneId: string | null;
  wingName: string | null;
  xsecIndex: number;
  spars: unknown[];
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sparError, setSparError] = useState<string | null>(null);
  const [width, setWidth] = useState("4.42");
  const [height, setHeight] = useState("4.42");
  const [posFactor, setPosFactor] = useState("0.25");
  const [sparMode, setSparMode] = useState("standard");
  const [sparLength, setSparLength] = useState("");
  const [sparStart, setSparStart] = useState("0");
  const [vecX, setVecX] = useState("");
  const [vecY, setVecY] = useState("");
  const [vecZ, setVecZ] = useState("");

  async function handleAddSpar() {
    if (!aeroplaneId || !wingName) return;
    setSaving(true);
    setSparError(null);
    try {
      const hasVector = vecX.trim() || vecY.trim() || vecZ.trim();
      const payload: Record<string, unknown> = {
        spare_support_dimension_width: parseFloat(width),
        spare_support_dimension_height: parseFloat(height),
        spare_position_factor: parseFloat(posFactor),
        spare_mode: sparMode,
        spare_start: sparStart.trim() ? parseFloat(sparStart) : 0,
      };
      if (sparLength.trim()) {
        payload.spare_length = parseFloat(sparLength);
      }
      if (hasVector) {
        payload.spare_vector = [
          parseFloat(vecX) || 0,
          parseFloat(vecY) || 0,
          parseFloat(vecZ) || 0,
        ];
      }
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/spars`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) throw new Error(`Add spar: ${res.status}`);
      onSaved();
    } catch (err: unknown) {
      setSparError(err instanceof Error ? err.message : "Spar save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 border-t border-border pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Spars ({spars.length})
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          {spars.length > 0 && (
            <p className="text-[11px] text-muted-foreground">
              {spars.length} spar(s) on this segment
            </p>
          )}
          <div className="flex gap-3">
            <Field label="width" value={width} suffix="mm" onChange={setWidth} />
            <Field label="height" value={height} suffix="mm" onChange={setHeight} />
          </div>
          <div className="flex gap-3">
            <Field label="position_factor" value={posFactor} onChange={setPosFactor} />
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">mode</label>
              <select
                value={sparMode}
                onChange={(e) => setSparMode(e.target.value)}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                {SPAR_MODES.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <Field label="length" value={sparLength} suffix="mm" onChange={setSparLength} />
            <Field label="start" value={sparStart} suffix="mm" onChange={setSparStart} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">
              direction (x, y, z) — empty = follow wing
            </label>
            <div className="flex gap-2">
              <input
                type="number" step="any" placeholder="x" value={vecX}
                onChange={(e) => setVecX(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <input
                type="number" step="any" placeholder="y" value={vecY}
                onChange={(e) => setVecY(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <input
                type="number" step="any" placeholder="z" value={vecZ}
                onChange={(e) => setVecZ(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
            </div>
          </div>
          <button
            onClick={handleAddSpar}
            disabled={saving}
            className="self-end rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Adding…" : "Add Spar"}
          </button>
          {sparError && <p className="text-[11px] text-red-500">{sparError}</p>}
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
