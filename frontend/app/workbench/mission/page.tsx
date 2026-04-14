import { Target, Radar, ChevronDown } from "lucide-react";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { AlertBanner } from "@/components/workbench/AlertBanner";
import { RadarChart } from "@/components/workbench/RadarChart";

const MISSION_AXES = [
  { key: "payload_mass", label: "Payload", max: 10 },
  { key: "flight_time", label: "Flight Time", max: 120 },
  { key: "cruise_speed", label: "Cruise Speed", max: 30 },
  { key: "range", label: "Range", max: 50 },
  { key: "ceiling", label: "Ceiling", max: 2000 },
];

const FORM_VALUES: Record<string, number> = {
  payload_mass: 2.5,
  flight_time: 45,
  cruise_speed: 14,
  range: 12,
  ceiling: 400,
};

function normalize(raw: Record<string, number>) {
  const result: Record<string, number> = {};
  for (const axis of MISSION_AXES) {
    result[axis.key] = Math.min(1, Math.max(0, (raw[axis.key] ?? 0) / axis.max));
  }
  return result;
}

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
      <div className="flex items-center gap-2 rounded-lg border border-border bg-input px-3 py-2">
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
  const targetValues = normalize(FORM_VALUES);

  return (
    <WorkbenchTwoPanel leftWidth={480}>
      {/* Left: Radar Chart Card */}
      <div className="flex h-full flex-col gap-4 rounded-[--radius-l] border border-border bg-card p-6">
        <div className="flex items-center gap-3">
          <Radar className="size-5 text-primary" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[18px] text-foreground">
            Mission Compliance
          </span>
        </div>
        <div className="flex-1">
          <RadarChart
            axes={MISSION_AXES.map((a) => ({ key: a.key, label: a.label }))}
            target={targetValues}
            analysis={null}
          />
        </div>
        <div className="flex items-center justify-center gap-5">
          <div className="flex items-center gap-1.5">
            <div className="size-2.5 rounded-[2px] bg-primary" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
              Target
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="size-2.5 rounded-[2px] bg-success" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
              Analysis
            </span>
          </div>
        </div>
      </div>

      {/* Right: Mission Objectives Card */}
      <div className="flex flex-col gap-6 rounded-[--radius-l] border border-border bg-card p-8">
        <div className="flex items-center gap-3">
          <Target className="size-5 text-primary" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] text-foreground">
            Mission Objectives
          </span>
        </div>

        <AlertBanner>
          Mission Objectives is waiting on backend resource. The form below
          renders but saving is disabled.
        </AlertBanner>

        <div className="flex flex-col gap-4 opacity-60">
          <div className="flex gap-4">
            <Field label="payload_mass" value="2.5" suffix="kg" />
            <Field label="flight_time" value="45" suffix="min" />
          </div>
          <div className="flex gap-4">
            <Field label="cruise_speed" value="14" suffix="m/s" />
            <Field label="range" value="12" suffix="km" />
          </div>
          <div className="flex gap-4">
            <Field label="ceiling" value="400" suffix="m" />
            <Field label="mission_type" value="surveillance" isSelect />
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2 text-[13px] text-muted-foreground">
            Cancel
          </button>
          <button className="rounded-[--radius-pill] border border-border bg-card-muted px-4 py-2 text-[13px] text-subtle-foreground">
            Save
          </button>
        </div>
      </div>
    </WorkbenchTwoPanel>
  );
}
