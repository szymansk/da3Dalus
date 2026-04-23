"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Check, Loader2, Pencil, Plus, Trash2, X } from "lucide-react";
import {
  createComponentType,
  deleteComponentType,
  updateComponentType,
  type ComponentType,
  type PropertyDefinition,
} from "@/hooks/useComponentTypes";
import { PropertyEditDialog } from "@/components/workbench/PropertyEditDialog";
import { useDialog } from "@/hooks/useDialog";

interface ComponentTypeEditDialogProps {
  open: boolean;
  type: ComponentType | null; // null = creating a new type
  onClose: () => void;
  onSaved: () => void;
}

interface TypeFormState {
  name: string;
  label: string;
  description: string;
  schema: PropertyDefinition[];
}

function toForm(t: ComponentType | null): TypeFormState {
  if (!t) return { name: "", label: "", description: "", schema: [] };
  return {
    name: t.name,
    label: t.label,
    description: t.description ?? "",
    schema: t.schema,
  };
}

const SNAKE_CASE = /^[a-z][a-z0-9_]*$/;

export function ComponentTypeEditDialog({
  open, type, onClose, onSaved,
}: Readonly<ComponentTypeEditDialogProps>) {
  const [form, setForm] = useState<TypeFormState>(toForm(type));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [propDialog, setPropDialog] = useState<{
    open: boolean;
    index: number | null;   // null = new
    initial: PropertyDefinition | null;
  }>({ open: false, index: null, initial: null });
  const [pendingDelete, setPendingDelete] = useState(false);
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const confirmDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (open) {
      setForm(toForm(type));
      setError(null);
    }
  }, [open, type]);

  // Manage confirm delete dialog
  useEffect(() => {
    const el = confirmDialogRef.current;
    if (!el) return;
    if (pendingDelete && !el.open) {
      el.showModal();
    } else if (!pendingDelete && el.open) {
      el.close();
    }
  }, [pendingDelete]);

  const closeConfirmDialog = useCallback(() => {
    setPendingDelete(false);
  }, []);

  const isNew = type === null;
  const canDeleteType = !isNew && type.deletable && type.reference_count === 0;

  function update(patch: Partial<TypeFormState>) {
    setForm((prev) => ({ ...prev, ...patch }));
  }

  async function handleSave() {
    if (!form.label.trim()) {
      setError("Label is required");
      return;
    }
    if (isNew) {
      if (!form.name.trim() || !SNAKE_CASE.test(form.name)) {
        setError("Name must be snake_case (lowercase + digits + underscores)");
        return;
      }
    }
    setSaving(true);
    setError(null);
    const payload = {
      name: form.name,
      label: form.label,
      description: form.description || null,
      schema: form.schema,
    };
    try {
      if (isNew) {
        await createComponentType(payload);
      } else {
        await updateComponentType(type.id, payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirmDelete() {
    if (!type) return;
    setSaving(true);
    try {
      await deleteComponentType(type.id);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPendingDelete(false);
    } finally {
      setSaving(false);
    }
  }

  function openNewProperty() {
    setPropDialog({ open: true, index: null, initial: null });
  }

  function openEditProperty(i: number) {
    setPropDialog({ open: true, index: i, initial: form.schema[i] });
  }

  function handlePropSave(prop: PropertyDefinition) {
    setForm((prev) => {
      const next = [...prev.schema];
      if (propDialog.index == null) next.push(prop);
      else next[propDialog.index] = prop;
      return { ...prev, schema: next };
    });
    setPropDialog({ open: false, index: null, initial: null });
  }

  function handlePropDelete(i: number) {
    setForm((prev) => ({
      ...prev,
      schema: prev.schema.filter((_, idx) => idx !== i),
    }));
  }

  const heading = isNew ? "New Type:" : `Edit Type: ${type.label}`;

  return (
    <>
      <dialog
        ref={dialogRef}
        className="m-auto bg-transparent backdrop:bg-black/60"
        onClose={handleClose}
        aria-label={heading}
      >
        <div className="flex w-[560px] max-h-[85vh] flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-2xl">
          <div className="flex items-center gap-2">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[15px] text-foreground">
              {heading}
            </span>
            <span className="flex-1" />
            {canDeleteType && (
              <button
                onClick={() => setPendingDelete(true)}
                title="Delete type"
                className="flex size-7 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20"
              >
                <Trash2 size={12} />
              </button>
            )}
            <button
              onClick={onClose}
              title="Close"
              className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={12} />
            </button>
          </div>

          <div className="flex flex-col gap-2 overflow-y-auto">
            <div className="flex gap-2">
              <div className="flex flex-1 flex-col gap-1">
                <label htmlFor="cte-name" className="text-[11px] text-muted-foreground">Name (snake_case)</label>
                <input
                  id="cte-name"
                  type="text"
                  value={form.name}
                  onChange={(e) => update({ name: e.target.value })}
                  disabled={!isNew}
                  placeholder="carbon_tube"
                  className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground disabled:opacity-60"
                />
              </div>
              <div className="flex flex-1 flex-col gap-1">
                <label htmlFor="cte-label" className="text-[11px] text-muted-foreground">Label *</label>
                <input
                  id="cte-label"
                  type="text"
                  value={form.label}
                  onChange={(e) => update({ label: e.target.value })}
                  placeholder="Carbon Tube"
                  className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="cte-description" className="text-[11px] text-muted-foreground">Description</label>
              <input
                id="cte-description"
                type="text"
                value={form.description}
                onChange={(e) => update({ description: e.target.value })}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              />
            </div>

            <div className="mt-1 flex items-center gap-2">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
                Properties ({form.schema.length})
              </span>
              <span className="flex-1" />
              <button
                onClick={openNewProperty}
                className="flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-[12px] text-primary-foreground hover:opacity-90"
              >
                <Plus size={12} />
                Property
              </button>
            </div>

            <div className="flex flex-col gap-1.5">
              {form.schema.length === 0 ? (
                <p className="py-3 text-center text-[11px] text-muted-foreground">
                  No properties defined.
                </p>
              ) : (
                form.schema.map((prop, i) => (
                  <div
                    key={`${prop.name}-${i}`}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card-muted px-3 py-2 text-[12px]"
                  >
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-foreground">
                      {prop.name}
                    </span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">{prop.label}</span>
                    <span className="rounded-full bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px]">
                      {prop.type}
                    </span>
                    {prop.unit && <span className="text-subtle-foreground">{prop.unit}</span>}
                    {prop.required && (
                      <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[9px] text-primary">
                        required
                      </span>
                    )}
                    <span className="flex-1" />
                    <button
                      onClick={() => openEditProperty(i)}
                      title="Edit property"
                      className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                    >
                      <Pencil size={10} />
                    </button>
                    <button
                      onClick={() => handlePropDelete(i)}
                      title="Delete property"
                      className="flex size-6 items-center justify-center rounded-full text-destructive hover:bg-destructive/20"
                    >
                      <Trash2 size={10} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-destructive bg-destructive/10 p-2 text-[11px] text-destructive">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              disabled={saving}
              className="rounded-full border border-border px-3 py-1.5 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {saving ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
              Save
            </button>
          </div>
        </div>
      </dialog>

      {propDialog.open && (
        <PropertyEditDialog
          // Rebind state when the target changes (index or "new")
          key={propDialog.index ?? "new"}
          open={true}
          initial={propDialog.initial}
          onSave={handlePropSave}
          onCancel={() => setPropDialog({ open: false, index: null, initial: null })}
        />
      )}

      <dialog
        ref={confirmDialogRef}
        className="m-auto bg-transparent backdrop:bg-black/60"
        onClose={closeConfirmDialog}
        aria-label="Confirm delete type"
      >
        {type && (
          <div className="flex w-[400px] flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-2xl">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[15px] text-foreground">
              Delete type &quot;{type.label}&quot;?
            </span>
            <p className="text-[12px] text-muted-foreground">
              The type has no references. Deletion is permanent.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPendingDelete(false)}
                className="rounded-full border border-border px-3 py-1.5 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="rounded-full bg-destructive px-3 py-1.5 text-[12px] text-destructive-foreground hover:opacity-90"
              >
                Confirm
              </button>
            </div>
          </div>
        )}
      </dialog>
    </>
  );
}
