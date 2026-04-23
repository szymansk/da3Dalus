"use client";

import { useState, useEffect, useRef } from "react";
import { X, Loader2, Upload } from "lucide-react";
import { uploadConstructionPart } from "@/hooks/useConstructionParts";
import { useComponents } from "@/hooks/useComponents";
import { useDialog } from "@/hooks/useDialog";

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
}: Readonly<ConstructionPartUploadDialogProps>) {
  const [name, setName] = useState("");
  const [materialId, setMaterialId] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const { dialogRef, handleClose } = useDialog(open, onClose);

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
    <dialog
      ref={dialogRef}
      className="z-50 backdrop:bg-black/60"
      onClose={handleClose}
      aria-label="Upload Construction Part"
    >
      <div className="flex w-[500px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl">
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
            <label htmlFor="upload-part-name" className="text-[11px] text-muted-foreground">Name *</label>
            <input
              id="upload-part-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Bulkhead-A"
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="upload-part-file" className="text-[11px] text-muted-foreground">File * (.step / .stp / .stl)</label>
            <input
              id="upload-part-file"
              ref={fileRef}
              type="file"
              accept=".step,.stp,.stl"
              onChange={(e) => {
                const picked = e.target.files?.[0]?.name ?? "";
                setFileName(picked);
                // Convenience: seed the Name field from the filename (last
                // suffix stripped) only while the user hasn't typed a name.
                // We don't overwrite user-entered names.
                if (!name && picked) {
                  const dot = picked.lastIndexOf(".");
                  setName(dot > 0 ? picked.slice(0, dot) : picked);
                }
              }}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground file:mr-3 file:rounded-full file:border-0 file:bg-sidebar-accent file:px-3 file:py-1 file:text-[12px]"
            />
            {fileName && (
              <span className="text-[11px] text-subtle-foreground">
                Selected: {fileName}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="upload-part-material" className="text-[11px] text-muted-foreground">
              Material (optional)
            </label>
            <select
              id="upload-part-material"
              value={materialId}
              onChange={(e) => setMaterialId(e.target.value)}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            >
              <option value="">No material selected</option>
              {materials.map((m) => {
                const density = m.specs?.["density_kg_m3"];
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
    </dialog>
  );
}
