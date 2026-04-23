"use client";

import { useEffect, useId, useState } from "react";
import { AlertTriangle, Lock, Loader2, Save, Trash2, X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import {
  deleteTreeNode,
  updateTreeNode,
  type ComponentTreeNode,
  type ComponentTreeNodeUpdate,
} from "@/hooks/useComponentTree";
import { lockConstructionPart } from "@/hooks/useConstructionParts";
import { useComponents, type Component } from "@/hooks/useComponents";

interface NodePropertyPanelProps {
  node: ComponentTreeNode | null;
  aeroplaneId: string;
  /** Invoked after a successful save / delete / lock so the caller can refetch. */
  onMutate: () => void;
  /** Invoked when the user closes the panel (X button or after delete). */
  onClose: () => void;
}

// --------------------------------------------------------------------------- //
// Form state
// --------------------------------------------------------------------------- //

/** Snapshot of all editable fields; keeps save semantics simple. */
interface FormState {
  name: string;
  quantity: string;
  weight_override_g: string;
  material_id: string;
  print_type: string;
  scale_factor: string;
  pos_x: string;
  pos_y: string;
  pos_z: string;
  rot_x: string;
  rot_y: string;
  rot_z: string;
}

function nodeToForm(n: ComponentTreeNode): FormState {
  const s = (v: number | null | undefined): string =>
    v == null ? "" : String(v);
  return {
    name: n.name,
    quantity: String(n.quantity ?? 1),
    weight_override_g: s(n.weight_override_g),
    material_id: s(n.material_id),
    print_type: n.print_type ?? "",
    scale_factor: String(n.scale_factor ?? 1),
    pos_x: String(n.pos_x ?? 0),
    pos_y: String(n.pos_y ?? 0),
    pos_z: String(n.pos_z ?? 0),
    rot_x: String(n.rot_x ?? 0),
    rot_y: String(n.rot_y ?? 0),
    rot_z: String(n.rot_z ?? 0),
  };
}

function parseNumOrNull(s: string): number | null {
  const trimmed = s.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

function parseNum(s: string, fallback = 0): number {
  const v = parseNumOrNull(s);
  return v == null ? fallback : v;
}

// --------------------------------------------------------------------------- //
// ConfirmModal (mirror of the one used in ConstructionPartsGrid; inline to
// keep the component self-contained. Extraction is a candidate for a later
// shared primitive.)
// --------------------------------------------------------------------------- //

interface ConfirmModalProps {
  title: string;
  body: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmModal({ title, body, onConfirm, onCancel }: Readonly<ConfirmModalProps>) {
  const { dialogRef, handleClose } = useDialog(true, onCancel);
  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
      aria-label={title}
    >
      <div className="flex w-[420px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
          {title}
        </span>
        <p className="text-[13px] text-muted-foreground">{body}</p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-full bg-destructive px-4 py-2 text-[13px] text-destructive-foreground hover:opacity-90"
          >
            Confirm
          </button>
        </div>
      </div>
    </dialog>
  );
}

// --------------------------------------------------------------------------- //
// Small helper renderers
// --------------------------------------------------------------------------- //

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: "text" | "number";
  placeholder?: string;
}

function Field({ label, value, onChange, type = "text", placeholder }: Readonly<FieldProps>) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-[11px] text-muted-foreground">{label}</label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
      />
    </div>
  );
}

function SixDof({ form, update }: Readonly<{
  form: FormState;
  update: (patch: Partial<FormState>) => void;
}>) {
  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        <Field label="Pos X (mm)" type="number" value={form.pos_x} onChange={(v) => update({ pos_x: v })} />
        <Field label="Pos Y (mm)" type="number" value={form.pos_y} onChange={(v) => update({ pos_y: v })} />
        <Field label="Pos Z (mm)" type="number" value={form.pos_z} onChange={(v) => update({ pos_z: v })} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Field label="Rot X (°)" type="number" value={form.rot_x} onChange={(v) => update({ rot_x: v })} />
        <Field label="Rot Y (°)" type="number" value={form.rot_y} onChange={(v) => update({ rot_y: v })} />
        <Field label="Rot Z (°)" type="number" value={form.rot_z} onChange={(v) => update({ rot_z: v })} />
      </div>
    </>
  );
}

function MaterialSelect({
  materials, value, onChange,
}: Readonly<{
  materials: Component[];
  value: string;
  onChange: (v: string) => void;
}>) {
  const materialId = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={materialId} className="text-[11px] text-muted-foreground">Material</label>
      <select
        id={materialId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
      >
        <option value="">No material selected</option>
        {materials.map((m) => {
          const density = (m.specs as Record<string, unknown>)?.["density_kg_m3"];
          const label = density ? `${m.name} (${density} kg/m³)` : m.name;
          return (
            <option key={m.id} value={String(m.id)}>{label}</option>
          );
        })}
      </select>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Main component
// --------------------------------------------------------------------------- //

export function NodePropertyPanel({
  node,
  aeroplaneId,
  onMutate,
  onClose,
}: Readonly<NodePropertyPanelProps>) {
  const [form, setForm] = useState<FormState | null>(
    node ? nodeToForm(node) : null,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState(false);
  const [lockBusy, setLockBusy] = useState(false);
  const { dialogRef, handleClose: dialogHandleClose } = useDialog(!!node, onClose);

  const { components: materials } = useComponents("material");

  // Re-seed the form whenever the selected node changes.
  useEffect(() => {
    setForm(node ? nodeToForm(node) : null);
    setError(null);
  }, [node?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  if (!node || !form) return null;

  const isCots = node.node_type === "cots";
  const isCadShape = node.node_type === "cad_shape";
  const constructionPartId = node.construction_part_id ?? null;

  const original = nodeToForm(node);
  const dirty = (Object.keys(form) as (keyof FormState)[]).some(
    (k) => form[k] !== original[k],
  );

  function update(patch: Partial<FormState>) {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));
  }

  async function handleSave() {
    if (!form || !node) return;
    setSaving(true);
    setError(null);
    try {
      const payload: ComponentTreeNodeUpdate = {
        parent_id: node.parent_id,
        sort_index: node.sort_index,
        node_type: node.node_type,
        name: form.name.trim(),
        quantity: isCots ? Math.max(1, Math.floor(parseNum(form.quantity, 1))) : node.quantity,
        weight_override_g: parseNumOrNull(form.weight_override_g),
        // cad_shape-only fields; pass through as-is for other types so the
        // backend's PUT doesn't wipe them.
        material_id: isCadShape ? parseNumOrNull(form.material_id) : node.material_id ?? null,
        print_type: isCadShape ? (form.print_type || null) : node.print_type ?? null,
        scale_factor: isCadShape ? parseNum(form.scale_factor, 1) : node.scale_factor ?? 1,
        pos_x: isCadShape ? parseNum(form.pos_x) : node.pos_x ?? 0,
        pos_y: isCadShape ? parseNum(form.pos_y) : node.pos_y ?? 0,
        pos_z: isCadShape ? parseNum(form.pos_z) : node.pos_z ?? 0,
        rot_x: isCadShape ? parseNum(form.rot_x) : node.rot_x ?? 0,
        rot_y: isCadShape ? parseNum(form.rot_y) : node.rot_y ?? 0,
        rot_z: isCadShape ? parseNum(form.rot_z) : node.rot_z ?? 0,
        // Preserved-through fields (not editable in the panel):
        shape_key: node.shape_key ?? null,
        shape_hash: node.shape_hash ?? null,
        volume_mm3: node.volume_mm3 ?? null,
        area_mm2: node.area_mm2 ?? null,
        component_id: node.component_id ?? null,
        construction_part_id: constructionPartId,
      };
      await updateTreeNode(aeroplaneId, node.id, payload);
      onMutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setForm(nodeToForm(node!));
    setError(null);
  }

  async function handleConfirmDelete() {
    if (!node) return;
    try {
      await deleteTreeNode(aeroplaneId, node.id);
      setPendingDelete(false);
      onMutate();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPendingDelete(false);
    }
  }

  async function handleLockToggle() {
    if (!constructionPartId) return;
    setLockBusy(true);
    try {
      // We don't know the part's current lock state from the tree node, so
      // we infer from a companion field if present, else default to lock.
      // Simpler: rely on the caller (onMutate) to refetch and show the
      // updated state; both operations are idempotent on the backend.
      // We use a toggle semantic: if the title is "Unlock part", call unlock.
      // The button's icon is keyed off locked state passed via prop convention.
      // For now, call lock (the management panel is the authoritative place
      // to unlock); treat this button as a shortcut.
      await lockConstructionPart(aeroplaneId, constructionPartId);
      onMutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLockBusy(false);
    }
  }

  const lockTitle = "Lock part";

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-transparent backdrop:bg-black/60"
      onClose={dialogHandleClose}
      onClick={(e) => { if (e.target === e.currentTarget) dialogHandleClose(); }}
      aria-label="Edit tree node"
    >
    <div
      className="flex max-h-[85vh] w-[480px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl"
    >
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
          {node.name}
        </span>
        <span className="rounded-full bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground uppercase">
          {node.node_type}
        </span>
        <span className="flex-1" />
        {isCadShape && (
          <button
            onClick={handleLockToggle}
            disabled={constructionPartId == null || lockBusy}
            title={lockTitle}
            className="flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-sidebar-accent disabled:opacity-40"
          >
            {lockBusy ? <Loader2 size={12} className="animate-spin" /> : <Lock size={12} />}
          </button>
        )}
        <button
          onClick={() => setPendingDelete(true)}
          title="Delete node"
          className="flex size-7 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20"
        >
          <Trash2 size={12} />
        </button>
        <button
          onClick={onClose}
          title="Close"
          className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
        >
          <X size={12} />
        </button>
      </div>

      {node.synced_from && (
        <div className="flex items-start gap-2 rounded-xl border border-primary/50 bg-primary/10 p-2.5">
          <AlertTriangle size={14} className="shrink-0 text-primary" />
          <span className="text-[11px] text-foreground">
            Synced from <span className="font-[family-name:var(--font-jetbrains-mono)]">{node.synced_from}</span> — changes may be overwritten on next sync.
          </span>
        </div>
      )}

      <div className="flex flex-col gap-3 overflow-y-auto">
        <Field
          label="Name"
          value={form.name}
          onChange={(v) => update({ name: v })}
        />
        <Field
          label="Weight override (g)"
          type="number"
          value={form.weight_override_g}
          onChange={(v) => update({ weight_override_g: v })}
          placeholder="blank = calculated"
        />

        {isCots && (
          <Field
            label="Quantity"
            type="number"
            value={form.quantity}
            onChange={(v) => update({ quantity: v })}
          />
        )}

        {isCadShape && (
          <>
            <MaterialSelect
              materials={materials}
              value={form.material_id}
              onChange={(v) => update({ material_id: v })}
            />
            <div className="grid grid-cols-2 gap-2">
              <Field
                label="Scale factor"
                type="number"
                value={form.scale_factor}
                onChange={(v) => update({ scale_factor: v })}
              />
              <div className="flex flex-col gap-1">
                <label htmlFor="npp-print-type" className="text-[11px] text-muted-foreground">Print type</label>
                <select
                  id="npp-print-type"
                  value={form.print_type}
                  onChange={(e) => update({ print_type: e.target.value })}
                  className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                >
                  <option value="">(inherit from material)</option>
                  <option value="volume">volume</option>
                  <option value="surface">surface</option>
                </select>
              </div>
            </div>
            <SixDof form={form} update={update} />
          </>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-destructive bg-destructive/10 p-2.5 text-[11px] text-destructive">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-2">
        <button
          onClick={handleCancel}
          disabled={!dirty || saving}
          className="rounded-full border border-border px-3 py-1.5 text-[12px] text-muted-foreground hover:bg-sidebar-accent disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          Save
        </button>
      </div>

      {pendingDelete && (
        <ConfirmModal
          title={`Delete "${node.name}"?`}
          body="This permanently removes the tree node and all its children."
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDelete(false)}
        />
      )}
    </div>
    </dialog>
  );
}
