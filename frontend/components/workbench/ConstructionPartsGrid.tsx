"use client";

import { useState } from "react";
import { Box, Lock, Unlock, Trash2, Upload, Loader2 } from "lucide-react";
import {
  useConstructionParts,
  lockConstructionPart,
  unlockConstructionPart,
  deleteConstructionPart,
  type ConstructionPart,
} from "@/hooks/useConstructionParts";
import { useDialog } from "@/hooks/useDialog";

interface ConstructionPartsGridProps {
  aeroplaneId: string;
  /** The upload flow lives in a sibling dialog owned by the page; opening it is the parent's job. */
  onRequestUpload: () => void;
}

function formatVolume(v: number | null): string {
  if (v == null) return "— mm³";
  if (v > 1e6) return `${(v / 1000).toFixed(1)} cm³`;
  return `${v.toFixed(0)} mm³`;
}

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

export function ConstructionPartsGrid({
  aeroplaneId,
  onRequestUpload,
}: Readonly<ConstructionPartsGridProps>) {
  const { parts, total, isLoading, mutate } = useConstructionParts(aeroplaneId);
  const [pendingDelete, setPendingDelete] = useState<ConstructionPart | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function handleLockToggle(part: ConstructionPart) {
    setBusyId(part.id);
    try {
      if (part.locked) {
        await unlockConstructionPart(aeroplaneId, part.id);
      } else {
        await lockConstructionPart(aeroplaneId, part.id);
      }
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lock toggle failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleConfirmDelete() {
    if (!pendingDelete) return;
    setBusyId(pendingDelete.id);
    try {
      await deleteConstructionPart(aeroplaneId, pendingDelete.id);
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusyId(null);
      setPendingDelete(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Box className="size-5 text-primary" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[18px] text-foreground">
          Construction Parts
        </span>
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {total} parts
        </span>
        <span className="flex-1" />
        <button
          onClick={onRequestUpload}
          className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90"
        >
          <Upload size={14} />
          Upload Part
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-12 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading construction parts...
        </div>
      )}
      {!isLoading && parts.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-12">
          <Box className="size-12 text-subtle-foreground" />
          <span className="text-[13px] text-muted-foreground">
            No construction parts yet. Upload one to get started.
          </span>
        </div>
      )}
      {!isLoading && parts.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {parts.map((part) => {
            const busy = busyId === part.id;
            return (
              <div
                key={part.id}
                className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
              >
                <div className="flex items-center gap-2">
                  <Box className="size-4 text-primary" />
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                    {part.name}
                  </span>
                  {part.file_format && (
                    <span className="rounded-full bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
                      {part.file_format.toUpperCase()}
                    </span>
                  )}
                  {part.locked && (
                    <span className="flex items-center gap-1 rounded-full bg-primary/20 px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-primary">
                      <Lock size={8} />
                      LOCKED
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                  <span className="font-[family-name:var(--font-jetbrains-mono)]">
                    {formatVolume(part.volume_mm3)}
                  </span>
                </div>

                <div className="flex justify-end gap-1.5">
                  <button
                    onClick={() => handleLockToggle(part)}
                    disabled={busy}
                    title={part.locked ? "Unlock part" : "Lock part"}
                    className="flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-sidebar-accent hover:text-foreground disabled:opacity-50"
                  >
                    {part.locked ? <Unlock size={12} /> : <Lock size={12} />}
                  </button>
                  <button
                    onClick={() => setPendingDelete(part)}
                    disabled={part.locked || busy}
                    title={
                      part.locked
                        ? "Delete blocked — unlock first"
                        : "Delete part"
                    }
                    className="flex size-7 items-center justify-center rounded-full border border-border text-destructive hover:bg-destructive/20 disabled:opacity-40"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {pendingDelete && (
        <ConfirmModal
          title={`Delete "${pendingDelete.name}"?`}
          body="The CAD file and its metadata will be permanently removed."
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}
