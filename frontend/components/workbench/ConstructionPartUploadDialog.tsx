"use client";

import { useState, useEffect, useRef } from "react";
import { X, Loader2, Upload } from "lucide-react";
import { uploadConstructionPart } from "@/hooks/useConstructionParts";
import { useComponents } from "@/hooks/useComponents";

interface ConstructionPartUploadDialogProps {
  open: boolean;
  aeroplaneId: string;
  onClose: () => void;
  onSaved: () => void;
}

export function ConstructionPartUploadDialog({
  open,
  aeroplaneId,
  onClose,
  onSaved,
}: ConstructionPartUploadDialogProps) {
  const [name, setName] = useState("");
  const [materialId, setMaterialId] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string>("");

  // Materials are queried from the existing COTS catalog.
  const { components: materials } = useComponents("material");

  useEffect(() => {
    if (open) {
      setName("");
      setMaterialId("");
      setFileName("");
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, [open]);

  if (!open) return null;

  const file = fileRef.current?.files?.[0] ?? null;
  const canSubmit = !!name.trim() && !!fileName && !saving;

  async function handleSubmit() {
    if (!file || !name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", name.trim());
      if (materialId) formData.append("material_component_id", materialId);
      await uploadConstructionPart(aeroplaneId, formData);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="flex w-[500px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Upload Construction Part"
      >
        <div className="flex items-center gap-3">
          <Upload size={16} className="text-primary" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            Upload Construction Part
          </span>
          <span className="flex-1" />
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Bulkhead-A"
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">File * (.step / .stp / .stl)</label>
            <input
              ref={fileRef}
              type="file"
              accept=".step,.stp,.stl"
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground file:mr-3 file:rounded-full file:border-0 file:bg-sidebar-accent file:px-3 file:py-1 file:text-[12px]"
            />
            {fileName && (
              <span className="text-[11px] text-subtle-foreground">
                Selected: {fileName}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">
              Material (optional)
            </label>
            <select
              value={materialId}
              onChange={(e) => setMaterialId(e.target.value)}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            >
              <option value="">No material selected</option>
              {materials.map((m) => {
                const density = (m.specs as Record<string, unknown>)?.["density_kg_m3"];
                const label = density
                  ? `${m.name} (${density} kg/m³)`
                  : m.name;
                return (
                  <option key={m.id} value={String(m.id)}>
                    {label}
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-destructive bg-destructive/10 p-3 text-[12px] text-destructive">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={saving}
            className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {saving ? "Uploading\u2026" : "Upload"}
          </button>
        </div>
      </div>
    </div>
  );
}
