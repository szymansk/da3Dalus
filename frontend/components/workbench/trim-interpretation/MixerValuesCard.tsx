"use client";

import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const ROLE_LABELS: Record<string, string> = {
  elevon: "Elevon",
  flaperon: "Flaperon",
  ruddervator: "Ruddervator",
};

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function MixerValuesCard({ enrichment }: Props) {
  if (!enrichment) return null;
  const entries = Object.entries(enrichment.mixer_values);
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        Mixer Setup
      </span>
      <div className="flex flex-col gap-3">
        {entries.map(([name, mixer]) => (
          <div key={name} className="rounded-lg border border-border/50 px-3 py-2">
            <span className="font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-foreground">
              {ROLE_LABELS[mixer.role] ?? mixer.role}
            </span>
            <div className="mt-1.5 grid grid-cols-2 gap-2">
              <div className="flex flex-col">
                <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                  Symmetric Offset
                </span>
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                  {mixer.symmetric_offset.toFixed(1)}&deg;
                </span>
              </div>
              <div className="flex flex-col">
                <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                  Differential Throw
                </span>
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                  {mixer.differential_throw.toFixed(1)}&deg;
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
