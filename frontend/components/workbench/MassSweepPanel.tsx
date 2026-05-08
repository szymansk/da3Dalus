"use client";

import { useState } from "react";
import type { MassSweepData, ComputeOptions } from "@/hooks/useMassSweep";
import { MassSweepChart } from "@/components/workbench/MassSweepChart";

interface Props {
  readonly data: MassSweepData | null;
  readonly isComputing: boolean;
  readonly error: string | null;
  readonly onCompute: (opts: ComputeOptions) => void;
  readonly currentMassKg: number | null;
}

export function MassSweepPanel({
  data,
  isComputing,
  error,
  onCompute,
  currentMassKg,
}: Props) {
  const [velocity, setVelocity] = useState(15);
  const [altitude, setAltitude] = useState(0);

  return (
    <div className="flex flex-col gap-3">
      {/* Header + Controls */}
      <div className="flex items-center gap-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Mass Sweep
        </span>
        <div className="flex-1" />

        <label className="flex items-center gap-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
          Velocity
          <input
            type="number"
            aria-label="Velocity"
            value={velocity}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (!Number.isNaN(v)) setVelocity(v);
            }}
            step={1}
            min={1}
            className="w-16 rounded-md border border-border bg-card px-2 py-1 text-[12px] text-foreground"
          />
          <span className="text-[10px]">m/s</span>
        </label>

        <label className="flex items-center gap-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
          Altitude
          <input
            type="number"
            aria-label="Altitude"
            value={altitude}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (!Number.isNaN(v)) setAltitude(v);
            }}
            step={100}
            min={0}
            className="w-20 rounded-md border border-border bg-card px-2 py-1 text-[12px] text-foreground"
          />
          <span className="text-[10px]">m</span>
        </label>

        <button
          onClick={() => onCompute({ velocity, altitude })}
          disabled={isComputing}
          className="flex items-center gap-1.5 rounded-full bg-[#FF8400] px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isComputing ? "Computing..." : "Compute Mass Sweep"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-red-400">
            {error}
          </span>
        </div>
      )}

      {/* Empty state */}
      {!data && !isComputing && !error && (
        <div className="flex items-center justify-center rounded-xl border border-border bg-card py-10">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Click Compute Mass Sweep to visualize metrics across mass range
          </span>
        </div>
      )}

      {/* Loading state */}
      {isComputing && !data && (
        <div className="flex items-center justify-center rounded-xl border border-border bg-card py-10">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Computing mass sweep...
          </span>
        </div>
      )}

      {/* Chart */}
      {data && (
        <div className="rounded-xl border border-border bg-card">
          <MassSweepChart points={data.points} currentMassKg={currentMassKg} />
        </div>
      )}
    </div>
  );
}
