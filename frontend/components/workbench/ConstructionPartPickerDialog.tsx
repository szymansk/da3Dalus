"use client";

import { useState } from "react";
import { X, Search, Loader2, Box, Lock } from "lucide-react";
import { useConstructionParts, type ConstructionPart } from "@/hooks/useConstructionParts";
import { useDialog } from "@/hooks/useDialog";

interface ConstructionPartPickerDialogProps {
  open: boolean;
  aeroplaneId: string;
  onClose: () => void;
  onSelect: (part: ConstructionPart) => void;
  /** Optional — surfaced in the header so the user knows where the part lands. */
  targetGroupName?: string;
}

function formatVolume(volume_mm3: number | null): string {
  if (volume_mm3 == null) return "— mm³";
  if (volume_mm3 > 1e6) return `${(volume_mm3 / 1000).toFixed(1)} cm³`;
  return `${volume_mm3.toFixed(0)} mm³`;
}

export function ConstructionPartPickerDialog({
  open,
  aeroplaneId,
  onClose,
  onSelect,
  targetGroupName,
}: Readonly<ConstructionPartPickerDialogProps>) {
  const [search, setSearch] = useState("");
  const { parts, total, isLoading } = useConstructionParts(open ? aeroplaneId : null);
  const { dialogRef, handleClose } = useDialog(open, onClose);

  const filtered = search.trim()
    ? parts.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    : parts;

  function handlePick(part: ConstructionPart) {
    onSelect(part);
    onClose();
  }

  const heading = targetGroupName
    ? `Assign Construction Part to '${targetGroupName}'`
    : "Assign Construction Part";

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
      onKeyDown={(e) => { if (e.key === "Escape") handleClose(); }}
      aria-label="Construction-Part picker"
    >
      <div className="flex max-h-[80vh] w-[560px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {heading}
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            {total} parts
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

        <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
          <Search className="size-3.5 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search parts..."
            className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
          />
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-[13px] text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Loading construction parts...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10 text-[13px] text-muted-foreground">
              <Box className="size-8 text-subtle-foreground" />
              <span>
                {parts.length === 0
                  ? "No construction parts available"
                  : "No parts match the filter"}
              </span>
            </div>
          ) : (
            filtered.map((part) => (
              <button
                key={part.id}
                onClick={() => handlePick(part)}
                className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2 text-left hover:border-primary hover:bg-sidebar-accent"
              >
                <div className="flex flex-1 flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                      {part.name}
                    </span>
                    {part.locked && (
                      <Lock size={11} className="text-primary" />
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    {part.file_format && (
                      <span className="rounded-full bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px]">
                        {part.file_format.toUpperCase()}
                      </span>
                    )}
                    <span className="font-[family-name:var(--font-jetbrains-mono)]">
                      {formatVolume(part.volume_mm3)}
                    </span>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
        </div>
      </div>
    </dialog>
  );
}
