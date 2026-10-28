"use client";

import { useEffect, useId, useState } from "react";
import { useSurfaceTypeActions } from "@/hooks/useSurfaceType";
import {
  PROPOSED_TOOLTIP,
  SURFACE_TYPES,
  SURFACE_TYPE_HINTS,
  SURFACE_TYPE_LABELS,
  type SurfaceType,
} from "@/lib/surfaceType";

const SELECT_CLASS =
  "w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground outline-none focus:border-primary";

/** Amber marker for a role that was only proposed and is not confirmed yet. */
export function ProposedBadge({ className = "" }: Readonly<{ className?: string }>) {
  return (
    <span
      title={PROPOSED_TOOLTIP}
      data-testid="surface-type-proposed"
      className={`rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-400 ${className}`}
    >
      Proposed
    </span>
  );
}

interface RoleSelectProps {
  id: string;
  label: string;
  value: SurfaceType;
  onChange: (v: SurfaceType) => void;
  options?: readonly SurfaceType[];
  disabledOptions?: readonly SurfaceType[];
}

/** Labelled role dropdown with a one-line hint for the chosen option. */
export function SurfaceTypeSelect({
  id,
  label,
  value,
  onChange,
  options = SURFACE_TYPES,
  disabledOptions = [],
}: Readonly<RoleSelectProps>) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-[11px] text-muted-foreground">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as SurfaceType)}
        className={SELECT_CLASS}
      >
        {options.map((t) => (
          <option key={t} value={t} disabled={disabledOptions.includes(t)}>
            {SURFACE_TYPE_LABELS[t]}
          </option>
        ))}
      </select>
      <p className="mt-1 text-[11px] text-muted-foreground">{SURFACE_TYPE_HINTS[value]}</p>
    </div>
  );
}

interface WingSurfaceTypePanelProps {
  aeroplaneId: string | null;
  wing: { name: string; surface_type?: SurfaceType; surface_type_inferred?: boolean };
  allWings: ReadonlyArray<{ name: string; surface_type?: SurfaceType }>;
}

/** Wing-level role editor: change the role (with swap when taking over main_wing) or confirm a proposal. */
export function WingSurfaceTypePanel({ aeroplaneId, wing, allWings }: Readonly<WingSurfaceTypePanelProps>) {
  const baseId = useId();
  const current = wing.surface_type ?? "horizontal_tail";
  const inferred = wing.surface_type_inferred === true;
  const [selected, setSelected] = useState<SurfaceType>(current);
  const [former, setFormer] = useState<SurfaceType>("horizontal_tail");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setSurfaceType } = useSurfaceTypeActions(aeroplaneId);

  useEffect(() => {
    setSelected(current);
    setFormer("horizontal_tail");
    setError(null);
  }, [wing.name, current, inferred]);

  const otherMain = allWings.find((w) => w.surface_type === "main_wing" && w.name !== wing.name);
  const needsSwap = selected === "main_wing" && current !== "main_wing" && !!otherMain;
  const changed = selected !== current;
  const canSave = !busy && (changed || inferred) && (!needsSwap || !!former);

  async function run(body: { surface_type: SurfaceType; former_main_becomes?: SurfaceType }) {
    setBusy(true);
    setError(null);
    try {
      await setSurfaceType(wing.name, body);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function handleSave() {
    void run({
      surface_type: selected,
      ...(needsSwap && former ? { former_main_becomes: former } : {}),
    });
  }

  return (
    <div className="mt-2 rounded-xl border border-border bg-card-muted p-3" data-testid="wing-surface-type-panel">
      <div className="mb-2 flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
          {wing.name} &middot; Role
        </span>
        {inferred && <ProposedBadge />}
      </div>

      <SurfaceTypeSelect
        id={`${baseId}-role`}
        label="Wing role"
        value={selected}
        onChange={(v) => {
          setSelected(v);
          setFormer("horizontal_tail");
          setError(null);
        }}
      />

      {needsSwap && otherMain && (
        <div className="mt-2">
          <SurfaceTypeSelect
            id={`${baseId}-former`}
            label={`Current main wing (${otherMain.name}) becomes …`}
            value={former}
            options={SURFACE_TYPES.filter((t) => t !== "main_wing")}
            onChange={setFormer}
          />
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 rounded-xl border border-destructive bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
          {error}
        </p>
      )}

      <div className="mt-3 flex justify-end gap-2">
        {inferred && !changed && (
          <button
            type="button"
            onClick={() => void run({ surface_type: current })}
            disabled={busy}
            className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3.5 py-1.5 text-[12px] text-amber-400 hover:bg-amber-500/20 disabled:opacity-50"
          >
            Confirm
          </button>
        )}
        {changed && (
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="rounded-full bg-primary px-4 py-1.5 text-[12px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save role"}
          </button>
        )}
      </div>
    </div>
  );
}
