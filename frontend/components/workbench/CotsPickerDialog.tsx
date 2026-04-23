"use client";

import { useState } from "react";
import { X, Search, Loader2, Package } from "lucide-react";
import { useComponents, type Component } from "@/hooks/useComponents";
import { useDialog } from "@/hooks/useDialog";

interface CotsPickerDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (component: Component) => void;
  /** Optional — shown in the header to give the user context. */
  targetGroupName?: string;
}

const TYPE_FILTER_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "All types" },
  { value: "servo", label: "Servo" },
  { value: "brushless_motor", label: "Motor" },
  { value: "esc", label: "ESC" },
  { value: "battery", label: "Battery" },
  { value: "receiver", label: "Receiver" },
  { value: "flight_controller", label: "Flight Controller" },
  { value: "material", label: "Material" },
  { value: "propeller", label: "Propeller" },
  { value: "generic", label: "Generic" },
];

export function CotsPickerDialog({
  open,
  onClose,
  onSelect,
  targetGroupName,
}: Readonly<CotsPickerDialogProps>) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const { components, total, isLoading } = useComponents(
    typeFilter || undefined,
    search || undefined,
  );
  const { dialogRef, handleClose } = useDialog(open, onClose);

  function handlePick(comp: Component) {
    onSelect(comp);
    onClose();
  }

  const heading = targetGroupName
    ? `Assign Component to '${targetGroupName}'`
    : "Assign Component";

  return (
    <dialog
      ref={dialogRef}
      role="dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
      onKeyDown={(e) => { if (e.key === "Escape") handleClose(); }}
      aria-label="Component picker"
    >
      <div className="flex max-h-[80vh] w-[560px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {heading}
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            {total} items
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

        <div className="flex gap-3">
          <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
            <Search className="size-3.5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search components..."
              className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle-foreground"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[12px] text-foreground"
          >
            {TYPE_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center gap-2 py-10 text-[13px] text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Loading components...
            </div>
          )}
          {!isLoading && components.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-10 text-[13px] text-muted-foreground">
              <Package className="size-8 text-subtle-foreground" />
              <span>
                {search || typeFilter
                  ? "No components match the filter"
                  : "No components available"}
              </span>
            </div>
          )}
          {!isLoading && components.length > 0 &&
            components.map((comp) => (
              <button
                key={comp.id}
                onClick={() => handlePick(comp)}
                className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2 text-left hover:border-primary hover:bg-sidebar-accent"
              >
                <div className="flex flex-1 flex-col gap-0.5">
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                    {comp.name}
                  </span>
                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <span className="rounded-full bg-sidebar-accent px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px]">
                      {comp.component_type}
                    </span>
                    {comp.manufacturer && <span>{comp.manufacturer}</span>}
                    {comp.mass_g != null && (
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-foreground">
                        {comp.mass_g}g
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))
          }
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
