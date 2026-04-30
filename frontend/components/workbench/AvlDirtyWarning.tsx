"use client";

import { useDialog } from "@/hooks/useDialog";
import { AlertTriangle } from "lucide-react";

interface Props {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly onViewDiff: () => void;
  readonly onRegenerate: () => void;
}

export function AvlDirtyWarning({ open, onClose, onViewDiff, onRegenerate }: Props) {
  const { dialogRef, handleClose } = useDialog(open, onClose);

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label="Geometry changed warning"
    >
      <div className="w-[420px] rounded-xl border border-border bg-card p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-primary/10">
            <AlertTriangle size={20} className="text-primary" />
          </div>
          <div>
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
              Geometry Changed
            </h3>
            <p className="text-[12px] text-muted-foreground">
              The airplane geometry has changed since you last edited the AVL file.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onRegenerate}
            className="rounded-full border border-border bg-card-muted px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent"
          >
            Regenerate
          </button>
          <button
            onClick={onViewDiff}
            className="rounded-full bg-primary px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground transition-colors hover:opacity-90"
          >
            View Diff
          </button>
        </div>
      </div>
    </dialog>
  );
}
