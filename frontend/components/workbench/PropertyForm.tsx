"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useWing, type XSec } from "@/hooks/useWings";
import { API_BASE } from "@/lib/fetcher";

/** Parse a number input string, allowing empty/partial input during editing */
function num(v: string, fallback = 0): number {
  if (v === "" || v === "-" || v === ".") return fallback;
  const n = parseFloat(v);
  return isNaN(n) ? fallback : n;
}

// ── Types ───────────────────────────────────────────────────────

type Mode = "wingconfig" | "asb";

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
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
        {readOnly ? (
          <span className="text-[13px] text-foreground">{value}</span>
        ) : (
          <input
            type={type}
            step="any"
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
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

export function PropertyForm() {
  const { aeroplaneId, selectedWing, selectedXsecIndex, treeMode } =
    useAeroplaneContext();
  const { wing, updateXSec, mutate } = useWing(aeroplaneId, selectedWing);

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

  // WingConfig state
  const [wc, setWc] = useState<WingConfigState | null>(null);

  // Sync state when selection changes
  useEffect(() => {
    if (xsec) {
      setAsb(xsecToAsb(xsec));
    } else {
      setAsb(null);
    }
    if (wing && selectedXsecIndex !== null) {
      setWc(xsecsToWingConfig(wing.x_secs, selectedXsecIndex));
    } else {
      setWc(null);
    }
    setError(null);
  }, [xsec?.airfoil, xsec?.chord, xsec?.twist, selectedXsecIndex, wing]);

  // No segment selected
  if (selectedXsecIndex === null || !xsec) {
    return (
      <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
        <p className="py-6 text-center text-[12px] text-muted-foreground">
          Select a segment in the tree
        </p>
      </div>
    );
  }

  function handleCancel() {
    if (xsec) setAsb(xsecToAsb(xsec));
    if (wing && selectedXsecIndex !== null)
      setWc(xsecsToWingConfig(wing.x_secs, selectedXsecIndex));
    setError(null);
  }

  async function handleSaveAsb() {
    if (!asb) return;
    setSaving(true);
    setError(null);
    try {
      await updateXSec(selectedXsecIndex!, asbToPayload(asb));
      await mutate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveWingConfig() {
    if (!wc || !aeroplaneId || !selectedWing || !wing) return;
    setSaving(true);
    setError(null);
    try {
      // Build a WingConfiguration JSON from the current wing + edited segment
      const segments = wing.x_secs.slice(0, -1).map((rootXsec, i) => {
        const tipXsec = wing.x_secs[i + 1];
        const isEdited = i === selectedXsecIndex;
        const src = isEdited ? wc : null;

        return {
          root_airfoil: {
            airfoil: src?.root_airfoil ?? rootXsec.airfoil,
            chord: src?.root_chord ?? rootXsec.chord * 1000,
            dihedral_as_rotation_in_degrees: src?.root_dihedral ?? 0,
            incidence: src?.root_incidence ?? rootXsec.twist,
            rotation_point_rel_chord: src?.root_rotation_point ?? 0.25,
          },
          tip_airfoil: {
            airfoil: src?.tip_airfoil ?? tipXsec.airfoil,
            chord: src?.tip_chord ?? tipXsec.chord * 1000,
            dihedral_as_rotation_in_degrees: src?.tip_dihedral ?? 0,
            incidence: src?.tip_incidence ?? tipXsec.twist,
            rotation_point_rel_chord: src?.tip_rotation_point ?? 0.25,
          },
          length: src?.length ?? Math.abs((tipXsec.xyz_le[1] - rootXsec.xyz_le[1]) * 1000),
          sweep: src?.sweep ?? (tipXsec.xyz_le[0] - rootXsec.xyz_le[0]) * 1000,
          number_interpolation_points: src?.number_interpolation_points ?? rootXsec.number_interpolation_points ?? 201,
          tip_type: src?.tip_type || rootXsec.tip_type || undefined,
        };
      });

      const wingConfig = {
        segments,
        nose_pnt: [
          wing.x_secs[0].xyz_le[0] * 1000,
          wing.x_secs[0].xyz_le[1] * 1000,
          wing.x_secs[0].xyz_le[2] * 1000,
        ],
        parameters: "relative",
        symmetric: wing.symmetric,
      };

      // Delete the existing wing first — from-wingconfig creates a new one
      await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${selectedWing}`,
        { method: "DELETE" },
      );

      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${selectedWing}/from-wingconfig`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(wingConfig),
        },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Save failed: ${res.status} ${body}`);
      }
      await mutate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const handleSave = mode === "wingconfig" ? handleSaveWingConfig : handleSaveAsb;

  return (
    <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
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
            {/* Row 1: root_airfoil | tip_airfoil */}
            <div className="flex gap-3">
              <Field
                label="root_airfoil"
                value={wc.root_airfoil}
                type="text"
                isSelect
                onChange={(v) => setWc({ ...wc, root_airfoil: v })}
              />
              <Field
                label="tip_airfoil"
                value={wc.tip_airfoil}
                type="text"
                isSelect
                onChange={(v) => setWc({ ...wc, tip_airfoil: v })}
              />
            </div>
            {/* Row 2: root_chord | tip_chord */}
            <div className="flex gap-3">
              <Field
                label="root_chord"
                value={wc.root_chord}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, root_chord: num(v) })}
              />
              <Field
                label="tip_chord"
                value={wc.tip_chord}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, tip_chord: num(v) })}
              />
            </div>
            {/* Row 3: length | sweep */}
            <div className="flex gap-3">
              <Field
                label="length"
                value={wc.length}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, length: num(v) })}
              />
              <Field
                label="sweep"
                value={wc.sweep}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, sweep: num(v) })}
              />
            </div>
            {/* Row 4: dihedral | incidence */}
            <div className="flex gap-3">
              <Field
                label="dihedral"
                value={wc.root_dihedral}
                suffix="°"
                onChange={(v) => setWc({ ...wc, root_dihedral: num(v) })}
              />
              <Field
                label="incidence"
                value={wc.root_incidence}
                suffix="°"
                onChange={(v) => setWc({ ...wc, root_incidence: num(v) })}
              />
            </div>
            {/* Row 5: rotation_point | interpolation_pts */}
            <div className="flex gap-3">
              <Field
                label="rotation_point"
                value={wc.root_rotation_point}
                onChange={(v) => setWc({ ...wc, root_rotation_point: num(v, 0.25) })}
              />
              <Field
                label="interpolation_pts"
                value={wc.number_interpolation_points}
                onChange={(v) => setWc({ ...wc, number_interpolation_points: num(v, 201) })}
              />
            </div>
          </>
        ) : asb ? (
          <>
            {/* ASB mode: airfoil | chord */}
            <div className="flex gap-3">
              <Field
                label="airfoil"
                value={asb.airfoil}
                type="text"
                onChange={(v) => setAsb({ ...asb, airfoil: v })}
              />
              <Field
                label="chord"
                value={asb.chord}
                suffix="mm"
                onChange={(v) => setAsb({ ...asb, chord: num(v) })}
              />
            </div>
            {/* twist | x_sec_type */}
            <div className="flex gap-3">
              <Field
                label="twist"
                value={asb.twist}
                suffix="°"
                onChange={(v) => setAsb({ ...asb, twist: num(v) })}
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
            className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-[--radius-pill] bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving\u2026" : "Save"}
          </button>
        </div>
        {error && <p className="text-[12px] text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// ── TED Section ─────────────────────────────────────────────────

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
  const [name, setName] = useState("");
  const [hingePoint, setHingePoint] = useState("0.8");
  const [symmetric, setSymmetric] = useState(false);
  const [servoPlacement, setServoPlacement] = useState("top");
  const [posDeg, setPosDeg] = useState("35");
  const [negDeg, setNegDeg] = useState("35");
  const [relChordTip, setRelChordTip] = useState("0.8");

  // Sync from existing TED
  useEffect(() => {
    if (ted && typeof ted === "object") {
      const t = ted as Record<string, unknown>;
      if (t.name) setName(String(t.name));
      if (t.hinge_point) setHingePoint(String(t.hinge_point));
      if (t.symmetric !== undefined) setSymmetric(Boolean(t.symmetric));
    }
  }, [ted]);

  const hasTed = ted && typeof ted === "object" && Object.keys(ted).length > 0;

  async function handleSaveTed() {
    if (!aeroplaneId || !wingName) return;
    setSaving(true);
    setTedError(null);
    try {
      // PATCH control surface
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

      // PATCH cad details
      const cadRes = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface/cad_details`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rel_chord_tip: parseFloat(relChordTip),
            servo_placement: servoPlacement,
            positive_deflection_deg: parseFloat(posDeg),
            negative_deflection_deg: parseFloat(negDeg),
          }),
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
          <div className="flex gap-3">
            <Field label="name" value={name} type="text" onChange={setName} />
            <Field label="hinge_point" value={hingePoint} onChange={setHingePoint} />
          </div>
          <div className="flex gap-3">
            <Field label="rel_chord_tip" value={relChordTip} onChange={setRelChordTip} />
            <Field label="servo_placement" value={servoPlacement} type="text" onChange={setServoPlacement} />
          </div>
          <div className="flex gap-3">
            <Field label="positive_deflection_deg" value={posDeg} suffix="°" onChange={setPosDeg} />
            <Field label="negative_deflection_deg" value={negDeg} suffix="°" onChange={setNegDeg} />
          </div>
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
            className="self-end rounded-[--radius-pill] bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
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

  async function handleAddSpar() {
    if (!aeroplaneId || !wingName) return;
    setSaving(true);
    setSparError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/spars`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            spare_support_dimension_width: parseFloat(width),
            spare_support_dimension_height: parseFloat(height),
            spare_position_factor: parseFloat(posFactor),
            spare_mode: sparMode,
          }),
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
            <Field label="mode" value={sparMode} type="text" onChange={setSparMode} />
          </div>
          <button
            onClick={handleAddSpar}
            disabled={saving}
            className="self-end rounded-[--radius-pill] bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Adding…" : "Add Spar"}
          </button>
          {sparError && <p className="text-[11px] text-red-500">{sparError}</p>}
        </div>
      )}
    </div>
  );
}
