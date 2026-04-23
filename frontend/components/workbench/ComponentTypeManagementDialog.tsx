"use client";

import { useState } from "react";
import { Lock, Pencil, Plus, Trash2, X } from "lucide-react";
import {
  useComponentTypes,
  type ComponentType,
} from "@/hooks/useComponentTypes";
import { ComponentTypeEditDialog } from "@/components/workbench/ComponentTypeEditDialog";
import { useDialog } from "@/hooks/useDialog";

interface ComponentTypeManagementDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ComponentTypeManagementDialog({
  open, onClose,
}: Readonly<ComponentTypeManagementDialogProps>) {
  const { types, isLoading, mutate, error } = useComponentTypes();
  const [editTarget, setEditTarget] = useState<{
    open: boolean;
    type: ComponentType | null; // null = create new
  }>({ open: false, type: null });
  const { dialogRef, handleClose } = useDialog(open, onClose);

  function startNew() {
    setEditTarget({ open: true, type: null });
  }

  function startEdit(t: ComponentType) {
    setEditTarget({ open: true, type: t });
  }

  function closeEdit() {
    setEditTarget({ open: false, type: null });
  }

  function deleteTitle(t: ComponentType): string {
    if (!t.deletable) return "Seeded type cannot be deleted";
    if (t.reference_count > 0) {
      return `Referenced by ${t.reference_count} component${t.reference_count === 1 ? "" : "s"} — cannot delete`;
    }
    return `Delete ${t.label}`;
  }

  return (
    <>
      <dialog
        ref={dialogRef}
        className="z-50 backdrop:bg-black/60"
        onClose={handleClose}
        aria-label="Manage Component Types"
      >
        <div className="flex w-[640px] max-h-[85vh] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl">
          <div className="flex items-center gap-2">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Manage Component Types
            </span>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
              {types.length}
            </span>
            <span className="flex-1" />
            <button
              onClick={startNew}
              className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90"
            >
              <Plus size={12} />
              New Type
            </button>
            <button
              onClick={onClose}
              title="Close"
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={14} />
            </button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {error && (
              <div className="rounded-xl border border-destructive bg-destructive/10 p-3 text-[12px] text-destructive">
                Failed to load types: {error instanceof Error ? error.message : String(error)}
                <p className="mt-2 text-[11px] opacity-70">
                  Make sure the backend exposes <code>/component-types</code>
                  {" "}(landed in PR #86).
                </p>
              </div>
            )}
            {!error && isLoading && (
              <p className="py-8 text-center text-[12px] text-muted-foreground">Loading…</p>
            )}
            {!error && !isLoading && types.length === 0 && (
              <p className="py-8 text-center text-[12px] text-muted-foreground">
                No types registered.
              </p>
            )}
            {!error && !isLoading && types.length > 0 &&
              types.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-2 rounded-xl border border-border bg-card-muted px-3 py-2 text-[13px]"
                >
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-foreground">
                    {t.label}
                  </span>
                  <span className="text-subtle-foreground">({t.name})</span>
                  {!t.deletable && (
                    <span title="Seeded (cannot be deleted)" className="text-muted-foreground">
                      <Lock size={10} />
                    </span>
                  )}
                  <span className="flex-1" />
                  <span className="text-[11px] text-muted-foreground">
                    {t.reference_count} components
                  </span>
                  <button
                    onClick={() => startEdit(t)}
                    title={`Edit ${t.label}`}
                    className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                  >
                    <Pencil size={12} />
                  </button>
                  <button
                    disabled={!t.deletable || t.reference_count > 0}
                    title={deleteTitle(t)}
                    className="flex size-7 items-center justify-center rounded-full text-destructive hover:bg-destructive/20 disabled:opacity-40"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            }
          </div>

          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Close
            </button>
          </div>
        </div>
      </dialog>

      <ComponentTypeEditDialog
        open={editTarget.open}
        type={editTarget.type}
        onClose={closeEdit}
        onSaved={() => mutate()}
      />
    </>
  );
}
