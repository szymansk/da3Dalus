import { Target, Info, ChevronDown } from "lucide-react";

function Field({
  label,
  value,
  suffix,
  isSelect,
}: {
  label: string;
  value: string;
  suffix?: string;
  isSelect?: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
        <span className="text-[13px] text-foreground">{value}</span>
        <span className="flex-1" />
        {isSelect ? (
          <ChevronDown className="size-3.5 text-muted-foreground" />
        ) : (
          suffix && (
            <span className="text-[11px] text-muted-foreground">{suffix}</span>
          )
        )}
      </div>
    </div>
  );
}

export default function MissionPage() {
  return (
    <div className="mx-auto flex w-full max-w-[960px] flex-col gap-6 rounded-[--radius-l] border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <Target className="size-5 text-primary" />
        <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
          Mission Objectives
        </h1>
      </div>

      {/* Alert banner */}
      <div className="flex items-start gap-3 rounded-[--radius-s] border border-primary bg-[#2A1F10] p-4">
        <Info className="size-4 shrink-0 text-primary" />
        <div className="flex flex-col gap-0.5">
          <span className="text-[13px] font-semibold text-foreground">
            Coming soon — backend wiring in progress
          </span>
          <span className="text-[12px] text-muted-foreground">
            Mission Objectives is waiting on backend resource. The form below
            renders but saving is disabled.
          </span>
        </div>
      </div>

      {/* Form grid */}
      <div className="flex flex-col gap-3 opacity-60">
        <div className="flex gap-3">
          <Field label="payload_mass" value="2.5" suffix="kg" />
          <Field label="flight_time" value="45" suffix="min" />
        </div>
        <div className="flex gap-3">
          <Field label="cruise_speed" value="14" suffix="m/s" />
          <Field label="range" value="12" suffix="km" />
        </div>
        <div className="flex gap-3">
          <Field label="ceiling" value="400" suffix="m" />
          <Field label="mission_type" value="surveillance" isSelect />
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <button className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2 text-[13px] text-muted-foreground">
          Cancel
        </button>
        <button className="rounded-[--radius-pill] border border-border bg-card-muted px-4 py-2 text-[13px] text-subtle-foreground">
          Save
        </button>
      </div>
    </div>
  );
}
