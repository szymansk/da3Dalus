"use client";

/**
 * Modal dialog for creating an immutable snapshot of the current head.
 *
 * Props:
 *   open       — controlled open state
 *   onClose    — called to close the dialog (Cancel / backdrop click / Escape)
 *   onSnapshot — async (label, note) → void; called when the user confirms
 */

import { useState, useCallback } from "react";
import { Camera } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";

export interface SnapshotDialogProps {
  open: boolean;
  onClose: () => void;
  onSnapshot: (label: string, note: string) => Promise<void>;
}

export function SnapshotDialog({ open, onClose, onSnapshot }: SnapshotDialogProps) {
  const [label, setLabel] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = useCallback(() => {
    if (saving) return;
    setLabel("");
    setNote("");
    setError(null);
    onClose();
  }, [saving, onClose]);

  const { dialogRef, handleClose: dialogHandleClose } = useDialog(open, handleClose);

  const handleSubmit = useCallback(async () => {
    const trimmed = label.trim();
    if (!trimmed) {
      setError("A label is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSnapshot(trimmed, note.trim());
      setLabel("");
      setNote("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Snapshot failed.");
    } finally {
      setSaving(false);
    }
  }, [label, note, onSnapshot, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        void handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/50"
      onClose={dialogHandleClose}
      aria-label="Save snapshot"
    >
      <div
        className="flex w-[440px] flex-col gap-5 rounded-[16px] border border-border bg-card p-6"
        onKeyDown={handleKeyDown}
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <Camera size={20} className="text-primary" />
          <span className="text-[16px] font-semibold text-foreground">Save Snapshot</span>
        </div>

        <p className="text-[13px] leading-relaxed text-muted-foreground">
          Saves an immutable copy of the current design. You can restore it later from
          the History &amp; Variants panel.
        </p>

        {/* Label */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="snapshot-label"
            className="text-[12px] font-medium text-foreground"
          >
            Label <span className="text-destructive" aria-hidden="true">*</span>
          </label>
          <input
            id="snapshot-label"
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. v2 — wider winglets"
            disabled={saving}
            autoFocus
            className="rounded-lg border border-border bg-card-muted px-3 py-2 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
            aria-required="true"
          />
        </div>

        {/* Note */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="snapshot-note"
            className="text-[12px] font-medium text-foreground"
          >
            Why? <span className="text-muted-foreground">(optional)</span>
          </label>
          <textarea
            id="snapshot-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Describe the reason or design goal for this snapshot…"
            disabled={saving}
            rows={3}
            className="resize-none rounded-lg border border-border bg-card-muted px-3 py-2 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
        </div>

        {/* Error */}
        {error && (
          <p role="alert" className="text-[12px] text-destructive">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={saving}
            className="rounded-xl bg-sidebar-accent px-5 py-2.5 text-[13px] font-medium text-muted-foreground hover:bg-sidebar-accent/80 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={saving || !label.trim()}
            className="rounded-xl bg-primary px-5 py-2.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            aria-label={saving ? "Saving snapshot…" : "Save snapshot"}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>

        <p className="text-[11px] text-muted-foreground">
          Tip: <kbd className="rounded border border-border px-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px]">⌘ Enter</kbd> to save.
        </p>
      </div>
    </dialog>
  );
}
