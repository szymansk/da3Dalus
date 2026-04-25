"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CreatorGallery } from "@/components/workbench/CreatorGallery";
import type { CreatorInfo } from "@/hooks/useCreators";

interface AddStepDialogProps {
  open: boolean;
  creators: CreatorInfo[];
  parentLabel: string;
  onClose: () => void;
  onSelect: (creator: CreatorInfo) => Promise<void> | void;
}

export function AddStepDialog({
  open,
  creators,
  parentLabel,
  onClose,
  onSelect,
}: Readonly<AddStepDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [submitting, setSubmitting] = useState(false);

  async function handleSelect(creator: CreatorInfo) {
    setSubmitting(true);
    try {
      await onSelect(creator);
      onClose();
    } catch (err) {
      alert(`Add step failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={`Add step to ${parentLabel}`}
    >
      {open && (
        <div className="flex max-h-[85vh] w-[640px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Add step to {parentLabel}
            </span>
            <span className="flex-1" />
            <button
              onClick={onClose}
              disabled={submitting}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent disabled:opacity-50"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body — Creator gallery */}
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-6 py-5">
            <CreatorGallery creators={creators} onSelect={handleSelect} />
          </div>
        </div>
      )}
    </dialog>
  );
}
