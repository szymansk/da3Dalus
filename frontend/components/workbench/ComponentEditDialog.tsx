"use client";

import { useState, useEffect } from "react";
import { X, Loader2 } from "lucide-react";
import type { Component } from "@/hooks/useComponents";
import { createComponent, updateComponent } from "@/hooks/useComponents";
import { useComponentTypes } from "@/hooks/useComponentTypes";

interface ComponentEditDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  component?: Component | null; // null = create new
}

export function ComponentEditDialog({ open, onClose, onSaved, component }: ComponentEditDialogProps) {
  const { types } = useComponentTypes();
  const isEdit = !!component;

  const [name, setName] = useState("");
  const [componentType, setComponentType] = useState("generic");
  const [manufacturer, setManufacturer] = useState("");
  const [description, setDescription] = useState("");
  const [massG, setMassG] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (component) {
      setName(component.name);
      setComponentType(component.component_type);
      setManufacturer(component.manufacturer ?? "");
      setDescription(component.description ?? "");
      setMassG(component.mass_g != null ? String(component.mass_g) : "");
    } else {
      setName("");
      setComponentType("generic");
      setManufacturer("");
      setDescription("");
      setMassG("");
    }
    setError(null);
  }, [component, open]);

  if (!open) return null;

  const handleSave = async () => {
    if (!name.trim()) { setError("Name is required"); return; }
    setSaving(true);
    setError(null);
    try {
      const data = {
        name: name.trim(),
        component_type: componentType,
        manufacturer: manufacturer.trim() || null,
        description: description.trim() || null,
        mass_g: massG ? parseFloat(massG) : null,
        bbox_x_mm: null,
        bbox_y_mm: null,
        bbox_z_mm: null,
        model_ref: null,
        specs: {},
      };
      if (isEdit && component) {
        await updateComponent(component.id, data as any);
      } else {
        await createComponent(data as any);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="flex w-[500px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {isEdit ? "Edit Component" : "New Component"}
          </span>
          <span className="flex-1" />
          <button onClick={onClose} className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent">
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Name *</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground" />
          </div>
          {/*
           * `min-w-0` on the flex items + `w-full` on the controls — same
           * pattern as the PropertyEditDialog Min/Max/Default fix. Without
           * it, a <select> element sizes to fit its longest option, which
           * can push the row wider than the modal when a user-added type
           * has a very long name. Reported 2026-04-16 for a garbage type
           * name of ~60 characters.
           */}
          <div className="flex gap-3">
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Type</label>
              <select value={componentType} onChange={(e) => setComponentType(e.target.value)}
                className="w-full truncate rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground">
                {types.map((t) => <option key={t.id} value={t.name}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Mass (g)</label>
              <input type="number" value={massG} onChange={(e) => setMassG(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground" />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Manufacturer</label>
            <input type="text" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground resize-none" />
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-destructive bg-destructive/10 p-3 text-[12px] text-destructive">{error}</div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={saving}
            className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent">
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50">
            {saving && <Loader2 size={14} className="animate-spin" />}
            {saving ? "Saving\u2026" : isEdit ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
