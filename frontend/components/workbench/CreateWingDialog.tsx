"use client";

import { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";
import { useDialog } from "@/hooks/useDialog";

type DesignModel = "wc" | "asb";

interface CreateWingDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string | null;
  onCreated?: (wingName: string, designModel: DesignModel) => void;
}

/** Default WingConfig payload for segment-based (WC) wing creation */
const DEFAULT_WINGCONFIG = {
  segments: [
    {
      root_airfoil: {
        airfoil: "naca0015",
        chord: 150,
        dihedral_as_rotation_in_degrees: 0,
        incidence: 0,
      },
      tip_airfoil: {
        airfoil: "naca0015",
        chord: 120,
        dihedral_as_rotation_in_degrees: 0,
        incidence: 0,
      },
      length: 500,
      sweep: 0,
    },
  ],
  nose_pnt: [0, 0, 0],
  symmetric: true,
};

/** Default ASB payload for position-based wing creation */
const DEFAULT_ASB_WING = {
  symmetric: true,
  x_secs: [
    { xyz_le: [0, 0, 0], chord: 0.15, twist: 0, airfoil: "naca0015" },
    { xyz_le: [0, 0.5, 0], chord: 0.12, twist: 0, airfoil: "naca0015" },
  ],
};

export function CreateWingDialog({
  open,
  onClose,
  aeroplaneId,
  onCreated,
}: Readonly<CreateWingDialogProps>) {
  const [name, setName] = useState("");
  const [designModel, setDesignModel] = useState<DesignModel>("wc");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { dialogRef, handleClose } = useDialog(open, onClose);

  // Focus the name input when dialog opens
  useEffect(() => {
    if (open) {
      setName("");
      setDesignModel("wc");
      setError(null);
      setCreating(false);
      // Small delay to let the dialog render
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  async function handleCreate() {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Wing name is required.");
      return;
    }
    if (!aeroplaneId) {
      setError("No aeroplane selected.");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      if (designModel === "wc") {
        // Create via WingConfig endpoint
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(trimmed)}/from-wingconfig`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(DEFAULT_WINGCONFIG),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Failed to create wing: ${res.status} ${body}`);
        }
      } else {
        // Create via ASB PUT endpoint (existing behavior)
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(trimmed)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: trimmed, ...DEFAULT_ASB_WING }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Failed to create wing: ${res.status} ${body}`);
        }
      }

      onCreated?.(trimmed, designModel);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !creating) {
      handleCreate();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
      aria-label="Create Wing"
    >
      {/* Dialog */}
      <div
        className="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card p-5 shadow-xl"
        onKeyDown={handleKeyDown}
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
            Create Wing
          </h3>
          <button
            onClick={onClose}
            className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          >
            <X size={14} />
          </button>
        </div>

        {/* Name input */}
        <div className="mb-4">
          <label htmlFor="wing-name" className="mb-1 block text-[11px] text-muted-foreground">
            Wing name
          </label>
          <input
            id="wing-name"
            ref={inputRef}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. main_wing"
            className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground outline-none placeholder:text-muted-foreground focus:border-primary"
          />
        </div>

        {/* Design model selection */}
        <fieldset className="mb-4 border-none p-0">
          <legend className="mb-2 block text-[11px] text-muted-foreground">
            Design model
          </legend>
          <div className="flex flex-col gap-2">
            <label
              aria-label="Segment-based (WC)"
              className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
                designModel === "wc"
                  ? "border-primary bg-primary/10"
                  : "border-border bg-card-muted hover:border-border-strong"
              }`}
            >
              <input
                type="radio"
                name="design_model"
                value="wc"
                checked={designModel === "wc"}
                onChange={() => setDesignModel("wc")}
                className="mt-0.5 accent-[#FF8400]"
              />
              <div>
                <span className="text-[13px] text-foreground">
                  Segment-based
                </span>
                <span className="ml-1.5 rounded bg-card-muted px-1 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-primary">
                  WC
                </span>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Define wing by segments with root/tip airfoils, length and sweep.
                </p>
              </div>
            </label>
            <label
              aria-label="Position-based (ASB)"
              className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
                designModel === "asb"
                  ? "border-primary bg-primary/10"
                  : "border-border bg-card-muted hover:border-border-strong"
              }`}
            >
              <input
                type="radio"
                name="design_model"
                value="asb"
                checked={designModel === "asb"}
                onChange={() => setDesignModel("asb")}
                className="mt-0.5 accent-[#FF8400]"
              />
              <div>
                <span className="text-[13px] text-foreground">
                  Position-based
                </span>
                <span className="ml-1.5 rounded bg-card-muted px-1 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-primary">
                  ASB
                </span>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Define wing by cross-sections with explicit 3D positions.
                </p>
              </div>
            </label>
          </div>
        </fieldset>

        {/* Error message */}
        {error && (
          <p className="mb-3 rounded-xl border border-destructive bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={creating}
            className="rounded-full border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating || !name.trim()}
            className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {creating ? "Creating\u2026" : "Create"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
