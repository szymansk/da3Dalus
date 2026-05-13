"use client";

/**
 * LoadingScenariosCard — CG Envelope from loading scenarios (gh-488).
 *
 * Displays:
 *  - CG envelope chip: SM = X.X% (forward) … Y.Y% (aft) with colour-coding
 *  - List of loading scenarios with CRUD actions
 *  - Template picker for quick scenario creation
 *  - Validation warnings when loading CG exceeds stability limits
 */

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
  XCircle,
  Layers,
} from "lucide-react";
import {
  type AircraftClass,
  type CgClassification,
  type CgEnvelope,
  type LoadingScenario,
  type LoadingScenarioCreate,
  AIRCRAFT_CLASS_LABELS,
  emptyOverrides,
  useLoadingScenarios,
  useCgEnvelope,
  useLoadingScenarioTemplates,
} from "@/hooks/useLoadingScenarios";

// ---------------------------------------------------------------------------
// Classification colours
// ---------------------------------------------------------------------------

function classificationColor(cls: CgClassification): string {
  switch (cls) {
    case "error":
      return "text-red-400";
    case "warn":
      return "text-orange-400";
    case "ok":
      return "text-green-400";
  }
}

function classificationBg(cls: CgClassification): string {
  switch (cls) {
    case "error":
      return "bg-red-500/10 border-red-500/30";
    case "warn":
      return "bg-orange-500/10 border-orange-500/30";
    case "ok":
      return "bg-green-500/10 border-green-500/30";
  }
}

function ClassificationIcon({ cls }: { readonly cls: CgClassification }) {
  switch (cls) {
    case "error":
      return <XCircle size={14} className="text-red-400" />;
    case "warn":
      return <AlertTriangle size={14} className="text-orange-400" />;
    case "ok":
      return <CheckCircle size={14} className="text-green-400" />;
  }
}

// ---------------------------------------------------------------------------
// CG Envelope chip
// ---------------------------------------------------------------------------

interface CgEnvelopeChipProps {
  readonly envelope: CgEnvelope;
}

function CgEnvelopeChip({ envelope }: CgEnvelopeChipProps) {
  const smFwdPct = (envelope.sm_at_fwd * 100).toFixed(1);
  const smAftPct = (envelope.sm_at_aft * 100).toFixed(1);
  const cls = envelope.classification;
  const color = classificationColor(cls);
  const bgCls = classificationBg(cls);

  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${bgCls}`}
      data-testid="cg-envelope-chip"
    >
      <ClassificationIcon cls={cls} />
      <span
        className={`font-[family-name:var(--font-jetbrains-mono)] text-[11px] ${color}`}
      >
        SM = {smFwdPct}% (fwd) &hellip; {smAftPct}% (aft)
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Template picker
// ---------------------------------------------------------------------------

interface TemplatePickerProps {
  readonly aeroplaneId: string;
  readonly aircraftClass: AircraftClass;
  readonly onCreate: (payload: LoadingScenarioCreate) => void;
}

function TemplatePicker({
  aeroplaneId,
  aircraftClass,
  onCreate,
}: TemplatePickerProps) {
  const { templates, isLoading } = useLoadingScenarioTemplates(
    aeroplaneId,
    aircraftClass,
  );

  if (isLoading) return null;

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        Templates
      </span>
      <div className="flex flex-wrap gap-1">
        {templates.map((t) => (
          <button
            key={t.name}
            onClick={() =>
              onCreate({
                name: t.name,
                aircraft_class: aircraftClass,
                component_overrides: t.component_overrides,
                is_default: t.is_default,
              })
            }
            className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:border-[#FF8400] hover:text-[#FF8400]"
          >
            {t.name}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scenario row
// ---------------------------------------------------------------------------

interface ScenarioRowProps {
  readonly scenario: LoadingScenario;
  readonly onDelete: (id: number) => void;
}

function ScenarioRow({ scenario, onDelete }: ScenarioRowProps) {
  const adhocCount = scenario.component_overrides.adhoc_items.length;

  return (
    <div
      className="flex items-center gap-2 rounded-md border border-border px-3 py-2"
      data-testid="scenario-row"
    >
      <div className="flex flex-1 flex-col gap-0.5">
        <span className="text-[12px] text-foreground">
          {scenario.name}
          {scenario.is_default && (
            <span className="ml-2 rounded-full bg-[#FF8400]/20 px-1.5 py-0.5 text-[9px] text-[#FF8400]">
              default
            </span>
          )}
        </span>
        {adhocCount > 0 && (
          <span className="text-[10px] text-muted-foreground">
            {adhocCount} adhoc item{adhocCount > 1 ? "s" : ""}
          </span>
        )}
      </div>
      <button
        onClick={() => onDelete(scenario.id)}
        className="text-muted-foreground hover:text-red-400"
        aria-label={`Delete ${scenario.name}`}
        data-testid="delete-scenario-button"
      >
        <Trash2 size={12} />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scenario list (extracted to avoid nested ternary)
// ---------------------------------------------------------------------------

interface ScenarioListProps {
  readonly scenarios: LoadingScenario[];
  readonly isLoading: boolean;
  readonly onDelete: (id: number) => void;
}

function ScenarioList({ scenarios, isLoading, onDelete }: ScenarioListProps) {
  if (isLoading) {
    return (
      <span className="text-[11px] text-muted-foreground">Loading…</span>
    );
  }
  if (scenarios.length === 0) {
    return (
      <span className="text-[11px] text-muted-foreground">
        No scenarios yet — add one to compute the CG envelope.
      </span>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      {scenarios.map((s) => (
        <ScenarioRow key={s.id} scenario={s} onDelete={onDelete} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add scenario form
// ---------------------------------------------------------------------------

interface AddScenarioFormProps {
  readonly aeroplaneId: string;
  readonly aircraftClass: AircraftClass;
  readonly onCreate: (payload: LoadingScenarioCreate) => void;
  readonly onCancel: () => void;
}

function AddScenarioForm({
  aeroplaneId,
  aircraftClass,
  onCreate,
  onCancel,
}: AddScenarioFormProps) {
  const [name, setName] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate({
      name: name.trim(),
      aircraft_class: aircraftClass,
      component_overrides: emptyOverrides(),
      is_default: false,
    });
  }

  return (
    <div className="flex flex-col gap-2">
      <TemplatePicker
        aeroplaneId={aeroplaneId}
        aircraftClass={aircraftClass}
        onCreate={onCreate}
      />
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Custom scenario name…"
          className="flex-1 rounded-md border border-border bg-sidebar px-2 py-1 text-[12px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-[#FF8400]"
          data-testid="scenario-name-input"
          autoFocus
        />
        <button
          type="submit"
          disabled={!name.trim()}
          className="rounded-md bg-[#FF8400] px-3 py-1 text-[11px] text-black disabled:opacity-50"
        >
          Add
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-[11px] text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

interface LoadingScenariosCardProps {
  readonly aeroplaneId: string;
}

export function LoadingScenariosCard({
  aeroplaneId,
}: LoadingScenariosCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [aircraftClass, setAircraftClass] = useState<AircraftClass>("rc_trainer");

  const { scenarios, isLoading, createScenario, deleteScenario } =
    useLoadingScenarios(aeroplaneId);
  const { envelope } = useCgEnvelope(aeroplaneId);

  async function handleCreate(payload: LoadingScenarioCreate) {
    try {
      await createScenario({ ...payload, aircraft_class: aircraftClass });
      setShowAdd(false);
    } catch {
      // error silently — toast/notification system is out of scope for this card
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteScenario(id);
    } catch {
      // error silently
    }
  }

  return (
    <div
      className="flex flex-col gap-2 rounded-lg border border-border bg-sidebar px-4 py-3"
      data-testid="loading-scenarios-card"
    >
      {/* Header */}
      <button
        className="flex items-center gap-2 text-left"
        onClick={() => setExpanded((v) => !v)}
        data-testid="loading-scenarios-header"
      >
        {expanded ? (
          <ChevronDown size={14} className="text-muted-foreground" />
        ) : (
          <ChevronRight size={14} className="text-muted-foreground" />
        )}
        <Layers size={14} className="text-[#FF8400]" />
        <span className="text-[12px] font-semibold text-foreground">
          Loading Scenarios
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground">
          {scenarios.length} scenario{scenarios.length !== 1 ? "s" : ""}
        </span>
      </button>

      {/* CG Envelope chip — always visible */}
      {envelope && <CgEnvelopeChip envelope={envelope} />}

      {/* Validation warnings */}
      {envelope && envelope.warnings.length > 0 && (
        <div className="flex flex-col gap-1">
          {envelope.warnings.map((w, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-md border border-orange-500/30 bg-orange-500/10 px-3 py-1.5"
            >
              <AlertTriangle
                size={12}
                className="mt-0.5 flex-shrink-0 text-orange-400"
              />
              <span className="text-[11px] text-orange-400">{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="flex flex-col gap-2 pt-1">
          {/* Aircraft class selector */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Aircraft class
            </span>
            <select
              value={aircraftClass}
              onChange={(e) => setAircraftClass(e.target.value as AircraftClass)}
              className="rounded border border-border bg-sidebar px-2 py-0.5 text-[11px] text-foreground"
              data-testid="aircraft-class-select"
            >
              {(
                Object.entries(AIRCRAFT_CLASS_LABELS) as [
                  AircraftClass,
                  string,
                ][]
              ).map(([val, label]) => (
                <option key={val} value={val}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Scenario list */}
          <ScenarioList
            scenarios={scenarios}
            isLoading={isLoading}
            onDelete={handleDelete}
          />

          {/* Add / template form */}
          {showAdd ? (
            <AddScenarioForm
              aeroplaneId={aeroplaneId}
              aircraftClass={aircraftClass}
              onCreate={handleCreate}
              onCancel={() => setShowAdd(false)}
            />
          ) : (
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 self-start text-[11px] text-muted-foreground hover:text-[#FF8400]"
              data-testid="add-scenario-button"
            >
              <Plus size={12} />
              Add scenario
            </button>
          )}
        </div>
      )}
    </div>
  );
}
