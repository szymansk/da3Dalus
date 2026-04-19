"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { X, Check, ChevronDown, ChevronUp, Search, ChevronRight } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";
import { useComponents, type Component } from "@/hooks/useComponents";

const HINGE_TYPES = ["middle", "top", "top_simple", "round_inside", "round_outside"] as const;

interface TedEditDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string;
  wingName: string;
  xsecIndex: number;
  isNew: boolean;
  initialData?: Record<string, unknown>;
  onSaved: () => void;
}

function optFloat(v: string): number | undefined {
  const trimmed = v.trim();
  if (!trimmed) return undefined;
  const n = parseFloat(trimmed);
  return Number.isFinite(n) ? n : undefined;
}

export function TedEditDialog({
  open,
  onClose,
  aeroplaneId,
  wingName,
  xsecIndex,
  isNew,
  initialData,
  onSaved,
}: TedEditDialogProps) {
  // Core fields
  const [name, setName] = useState("");
  const [hingePoint, setHingePoint] = useState("0.8");
  const [symmetric, setSymmetric] = useState(false);
  const [relChordTip, setRelChordTip] = useState("0.8");
  const [hingeType, setHingeType] = useState("top");
  const [posDeg, setPosDeg] = useState("35");
  const [negDeg, setNegDeg] = useState("35");

  // CAD details
  const [hingeSpacing, setHingeSpacing] = useState("");
  const [sideSpacingRoot, setSideSpacingRoot] = useState("");
  const [sideSpacingTip, setSideSpacingTip] = useState("");
  const [teOffsetFactor, setTeOffsetFactor] = useState("1.0");
  const [servoPlacement, setServoPlacement] = useState("top");
  const [servoChordPos, setServoChordPos] = useState("");
  const [servoLengthPos, setServoLengthPos] = useState("");

  const [cadOpen, setCadOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData && typeof initialData === "object") {
      const t = initialData;
      setName(String(t.name ?? ""));
      setHingePoint(String(t.hinge_point ?? "0.8"));
      setSymmetric(Boolean(t.symmetric));
      setRelChordTip(String(t.rel_chord_tip ?? "0.8"));
      setHingeType(String(t.hinge_type ?? "top"));
      setPosDeg(String(t.positive_deflection_deg ?? "35"));
      setNegDeg(String(t.negative_deflection_deg ?? "35"));
      setHingeSpacing(t.hinge_spacing != null ? String(t.hinge_spacing) : "");
      setSideSpacingRoot(t.side_spacing_root != null ? String(t.side_spacing_root) : "");
      setSideSpacingTip(t.side_spacing_tip != null ? String(t.side_spacing_tip) : "");
      setTeOffsetFactor(t.trailing_edge_offset_factor != null ? String(t.trailing_edge_offset_factor) : "1.0");
      setServoPlacement(String(t.servo_placement ?? "top"));
      setServoChordPos(t.rel_chord_servo_position != null ? String(t.rel_chord_servo_position) : "");
      setServoLengthPos(t.rel_length_servo_position != null ? String(t.rel_length_servo_position) : "");
    } else {
      setName("");
      setHingePoint("0.8");
      setSymmetric(false);
      setRelChordTip("0.8");
      setHingeType("top");
      setPosDeg("35");
      setNegDeg("35");
      setHingeSpacing("");
      setSideSpacingRoot("");
      setSideSpacingTip("");
      setTeOffsetFactor("1.0");
      setServoPlacement("top");
      setServoChordPos("");
      setServoLengthPos("");
    }
    setError(null);
  }, [initialData, open]);

  if (!open) return null;

  async function handleSave() {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    setError(null);
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

      // PATCH cad details
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
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this control surface?")) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface`,
        { method: "DELETE" },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${text}`);
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setSaving(false);
    }
  }

  const hasTed = !isNew;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-[480px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {isNew ? "Add Control Surface" : "Edit Control Surface"}
          </h2>
          <button
            onClick={onClose}
            className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
          >
            <X size={14} />
          </button>
        </div>

        {/* Fields */}
        <div className="flex flex-col gap-3">
          <div className="flex gap-3">
            <TedField label="Name" value={name} type="text" onChange={setName} />
            <TedField label="Hinge Point" value={hingePoint} onChange={setHingePoint} />
          </div>
          <div className="flex gap-3">
            <TedField label="Tip Chord" value={relChordTip} onChange={setRelChordTip} />
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Hinge Type</label>
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
          <div className="flex gap-3">
            <TedField label="Positive Deflection" value={posDeg} suffix="deg" onChange={setPosDeg} />
            <TedField label="Negative Deflection" value={negDeg} suffix="deg" onChange={setNegDeg} />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={symmetric}
              onChange={(e) => setSymmetric(e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-[11px] text-muted-foreground">Symmetric</span>
          </div>

          {/* CAD Details (collapsible) */}
          <div className="border-t border-border pt-2">
            <button
              onClick={() => setCadOpen(!cadOpen)}
              className="flex w-full items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
            >
              {cadOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              CAD Details
            </button>
            {cadOpen && (
              <div className="mt-2 flex flex-col gap-2">
                <div className="flex gap-3">
                  <TedField label="Hinge Spacing" value={hingeSpacing} suffix="mm" onChange={setHingeSpacing} />
                  <TedField label="TE Offset Factor" value={teOffsetFactor} onChange={setTeOffsetFactor} />
                </div>
                <div className="flex gap-3">
                  <TedField label="Side Spacing Root" value={sideSpacingRoot} suffix="mm" onChange={setSideSpacingRoot} />
                  <TedField label="Side Spacing Tip" value={sideSpacingTip} suffix="mm" onChange={setSideSpacingTip} />
                </div>
                <div className="flex gap-3">
                  <div className="flex flex-1 flex-col gap-1">
                    <label className="text-[11px] text-muted-foreground">Servo Placement</label>
                    <select
                      value={servoPlacement}
                      onChange={(e) => setServoPlacement(e.target.value)}
                      className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                    >
                      <option value="top">top</option>
                      <option value="bottom">bottom</option>
                    </select>
                  </div>
                  <div className="flex-1" />
                </div>
                <div className="flex gap-3">
                  <TedField label="Servo Chord Pos" value={servoChordPos} onChange={setServoChordPos} />
                  <TedField label="Servo Length Pos" value={servoLengthPos} onChange={setServoLengthPos} />
                </div>

                {/* Servo Picker */}
                {hasTed && (
                  <ServoPickerInDialog
                    aeroplaneId={aeroplaneId}
                    wingName={wingName}
                    xsecIndex={xsecIndex}
                    ted={initialData}
                    onAssigned={onSaved}
                  />
                )}
              </div>
            )}
          </div>
        </div>

        {/* Error */}
        {error && <p className="text-[12px] text-red-500">{error}</p>}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {!isNew && (
            <button
              onClick={handleDelete}
              disabled={saving}
              className="rounded-full border border-destructive px-3 py-2 text-[13px] text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              Delete
            </button>
          )}
          <span className="flex-1" />
          <button
            onClick={onClose}
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
            {saving ? "Saving..." : isNew ? "Add" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TedField({
  label,
  value,
  suffix,
  type = "number",
  onChange,
}: {
  label: string;
  value: string;
  suffix?: string;
  type?: "text" | "number";
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        <input
          type={type}
          step="any"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        {suffix && (
          <span className="flex-shrink-0 text-[11px] text-muted-foreground">{suffix}</span>
        )}
      </div>
    </div>
  );
}

/** Maps a Component's specs to the Servo CAD object expected by the API. */
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

function ServoPickerInDialog({
  aeroplaneId,
  wingName,
  xsecIndex,
  ted,
  onAssigned,
}: {
  aeroplaneId: string;
  wingName: string;
  xsecIndex: number;
  ted: Record<string, unknown> | null | undefined;
  onAssigned: () => void;
}) {
  const { components: servos } = useComponents("servo");

  const servoData = ted && typeof ted === "object"
    ? (ted as Record<string, unknown>).servo as Record<string, unknown> | null | undefined
    : null;
  const assignedComponentId = servoData && typeof servoData === "object"
    ? (servoData as Record<string, unknown>).component_id as number | null | undefined
    : null;
  const currentServoName = assignedComponentId
    ? servos.find((s) => s.id === assignedComponentId)?.name ?? `Servo #${assignedComponentId}`
    : servoData ? "Servo (unknown)" : null;

  const [pickerOpen, setPickerOpen] = useState(false);
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

  useEffect(() => {
    if (!pickerOpen) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [pickerOpen]);

  useEffect(() => {
    if (pickerOpen) searchRef.current?.focus();
  }, [pickerOpen]);

  async function assignServo(comp: Component) {
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
      if (!res.ok) throw new Error(`${res.status}`);
      setPickerOpen(false);
      setSearch("");
      onAssigned();
    } catch (err) {
      setServoError(err instanceof Error ? err.message : String(err));
    } finally {
      setAssigning(false);
    }
  }

  async function removeServo() {
    setAssigning(true);
    setServoError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/control_surface/cad_details/servo_details`,
        { method: "DELETE" },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      setPickerOpen(false);
      setSearch("");
      onAssigned();
    } catch (err) {
      setServoError(err instanceof Error ? err.message : String(err));
    } finally {
      setAssigning(false);
    }
  }

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">Servo</label>
      <button
        onClick={() => { setPickerOpen((v) => !v); if (pickerOpen) setSearch(""); }}
        disabled={assigning}
        className={`flex items-center gap-2 rounded-xl px-3 py-2 transition-colors ${
          pickerOpen ? "border-2 border-primary bg-input" : "border border-border bg-input"
        } disabled:opacity-50`}
      >
        <span className="text-[13px] text-foreground">{currentServoName || "None"}</span>
        <div className="flex-1" />
        {pickerOpen ? <ChevronUp size={12} className="text-primary" /> : <ChevronDown size={12} className="text-muted-foreground" />}
      </button>
      {pickerOpen && (
        <div className="absolute top-full z-50 mt-1 w-full rounded-xl border border-border bg-card shadow-lg">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search size={13} className="text-muted-foreground" />
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search servos..."
              className="flex-1 bg-transparent text-[13px] text-foreground placeholder:text-subtle-foreground outline-none"
            />
          </div>
          <div className="max-h-[200px] overflow-y-auto py-1">
            <button
              onClick={removeServo}
              disabled={assigning}
              className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-sidebar-accent disabled:opacity-50"
            >
              {!currentServoName ? <Check size={12} className="text-primary" /> : <div className="w-3" />}
              <span className="text-[13px] text-muted-foreground italic">None</span>
            </button>
            {filtered.map((s) => (
              <button
                key={s.id}
                onClick={() => assignServo(s)}
                disabled={assigning}
                className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-sidebar-accent disabled:opacity-50"
              >
                {s.name === currentServoName ? <Check size={12} className="text-primary" /> : <div className="w-3" />}
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">{s.name}</span>
                {s.manufacturer && <span className="text-[12px] text-muted-foreground">({s.manufacturer})</span>}
                {s.mass_g != null && (
                  <>
                    <span className="flex-1" />
                    <span className="text-[10px] text-subtle-foreground">{s.mass_g}g</span>
                  </>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
      {servoError && <p className="mt-1 text-[11px] text-red-500">{servoError}</p>}
    </div>
  );
}
