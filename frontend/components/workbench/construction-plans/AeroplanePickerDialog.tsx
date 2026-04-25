"use client";

import { useState } from "react";
import { Search, ChevronDown, X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import type { Aeroplane } from "@/hooks/useAeroplanes";

interface AeroplanePickerDialogProps {
  open: boolean;
  aeroplanes: Aeroplane[];
  title: string;
  onClose: () => void;
  onSelect: (aeroplaneId: string) => Promise<void> | void;
}

export function AeroplanePickerDialog({
  open,
  aeroplanes,
  title,
  onClose,
  onSelect,
}: Readonly<AeroplanePickerDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [search, setSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const filtered = aeroplanes.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  );

  async function handlePick(id: string) {
    setSubmitting(true);
    try {
      await onSelect(id);
      onClose();
    } catch (err) {
      alert(`Failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={title}
    >
      {open && (
        <div className="flex max-h-[85vh] w-[480px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              {title}
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

          {/* Body */}
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-6 py-5">
            <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
              <Search className="size-3.5 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search aeroplanes..."
                className="flex-1 bg-transparent text-[13px] text-foreground outline-none placeholder:text-subtle-foreground"
                autoFocus
              />
              <ChevronDown size={12} className="text-muted-foreground" />
            </div>
            <div className="flex flex-col gap-1 max-h-[400px] overflow-y-auto">
              {filtered.length === 0 ? (
                <p className="px-3 py-2 text-[12px] text-muted-foreground">
                  No aeroplanes found
                </p>
              ) : (
                filtered.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    disabled={submitting}
                    onClick={() => handlePick(a.id)}
                    className="block w-full rounded-lg px-3 py-2 text-left text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
                  >
                    <span className="font-[family-name:var(--font-jetbrains-mono)]">
                      {a.name}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </dialog>
  );
}
