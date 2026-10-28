"use client";

import { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";
import { useDialog } from "@/hooks/useDialog";
import { SurfaceTypeSelect } from "./WingSurfaceType";
import { extractErrorDetail, type SurfaceType } from "@/lib/surfaceType";

type DesignModel = "wc" | "asb";

interface CreateWingDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string | null;
  onCreated?: (wingName: string, designModel: DesignModel) => void;
  /** Name of the aeroplane's current main wing, if any (a second main wing is rejected). */
  mainWingName?: string | null;
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
  mainWingName = null,
}: Readonly<CreateWingDialogProps>) {
  const [name, setName] = useState("");
  const [designModel, setDesignModel] = useState<DesignModel>("wc");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [surfaceType, setSurfaceType] = useState<SurfaceType>("horizontal_tail");
  const hasMainWing = !!mainWingName;
  const inputRef = useRef<HTMLInputElement>(null);
  const { dialogRef, handleClose } = useDialog(open, onClose);

  // Focus the name input when dialog opens
  useEffect(() => {
    if (open) {
      setName("");
      setDesignModel("wc");
      setSurfaceType(hasMainWing ? "horizontal_tail" : "main_wing");
      setError(null);
      setCreating(false);
      // Small delay to let the dialog render
      setTimeout(() => inputRef.current?.focus(), 50);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // The wing list may load after the dialog opened: never leave a blocked choice selected.
  useEffect(() => {
    if (hasMainWing && surfaceType === "main_wing") setSurfaceType("horizontal_tail");
  }, [hasMainWing, surfaceType]);

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
            body: JSON.stringify({ ...DEFAULT_WINGCONFIG, surface_type: surfaceType }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Failed to create wing: ${extractErrorDetail(body, res.status)}`);
        }
      } else {
        // Create via ASB PUT endpoint (existing behavior)
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(trimmed)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: trimmed, ...DEFAULT_ASB_WING, surface_type: surfaceType }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Failed to create wing: ${extractErrorDetail(body, res.status)}`);
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
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label="Create Wing"
    >
      {/* Dialog */}
      <form
        className="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card p-5 shadow-xl"
        onKeyDown={handleKeyDown}
        onSubmit={(e) => e.preventDefault()}
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

        {/* Wing role (GH-1187) */}
        <div className="mb-4">
          <SurfaceTypeSelect
            id="wing-surface-type"
            label="Wing role"
            value={surfaceType}
            onChange={setSurfaceType}
            disabledOptions={hasMainWing ? ["main_wing"] : []}
          />
          {hasMainWing && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              Main wing is unavailable: &quot;{mainWingName}&quot; is already the main wing. Change roles on the existing wing first.
            </p>
          )}
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
      </form>
    </dialog>
  );
}
