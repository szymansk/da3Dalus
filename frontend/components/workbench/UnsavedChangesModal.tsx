"use client";

import { TriangleAlert } from "lucide-react";
import { useUnsavedChanges } from "@/components/workbench/UnsavedChangesContext";

export function UnsavedChangesModal() {
  const { pendingHref, isSaving, confirmDiscard, confirmSave, cancelNavigation } = useUnsavedChanges();

  if (!pendingHref) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={cancelNavigation}
    >
      <div
        className="flex w-[460px] flex-col gap-5 rounded-[16px] border border-border bg-card p-6"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => { if (e.key === "Escape") cancelNavigation(); }}
      >
        <div className="flex items-center gap-3">
          <TriangleAlert size={24} className="text-primary" />
          <span className="text-[18px] font-semibold text-foreground">
            Unsaved Changes
          </span>
        </div>
        <p className="text-[14px] leading-relaxed text-muted-foreground">
          You have unsaved changes. Do you want to save before leaving?
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={confirmDiscard}
            disabled={isSaving}
            className="rounded-[--radius-s] border border-destructive px-5 py-2.5 text-[14px] font-medium text-destructive disabled:opacity-50"
          >
            Discard
          </button>
          <button
            onClick={cancelNavigation}
            disabled={isSaving}
            className="rounded-[--radius-s] bg-sidebar-accent px-5 py-2.5 text-[14px] font-medium text-muted-foreground disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={confirmSave}
            disabled={isSaving}
            className="rounded-[--radius-s] bg-primary px-5 py-2.5 text-[14px] font-medium text-primary-foreground disabled:opacity-50"
          >
            {isSaving ? "Saving\u2026" : "Save & Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
