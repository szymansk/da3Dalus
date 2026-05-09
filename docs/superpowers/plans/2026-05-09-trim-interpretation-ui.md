# Trim Interpretation UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5 rich UI components in the OP detail drawer that translate raw trim numbers into actionable design decisions — analysis goal summary, control authority chart, expandable warnings, mixer cards, and multi-OP comparison table.

**Architecture:** Extract new components from the 898-line `OperatingPointsPanel.tsx` into `frontend/components/workbench/trim-interpretation/`. Each component receives `TrimEnrichment` (or `StoredOperatingPoint[]` for comparison). Uses Plotly for the authority chart (consistent with VnDiagram/StabilitySideView), Tailwind for everything else. One small backend schema addition (`aero_coefficients` field on `TrimEnrichment`) enables the comparison table's CL/CD/L÷D columns.

**Tech Stack:** TypeScript, React 19, Plotly.js (dynamic import), Tailwind CSS, Vitest + testing-library, Playwright-BDD

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/components/workbench/trim-interpretation/AnalysisGoalCard.tsx` | Goal + result summary + status badge |
| Create | `frontend/components/workbench/trim-interpretation/ControlAuthorityChart.tsx` | Plotly horizontal bar chart |
| Create | `frontend/components/workbench/trim-interpretation/DesignWarningBadges.tsx` | Expandable warning badges |
| Create | `frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx` | Dual-role surface mixer display |
| Create | `frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx` | Multi-OP sortable table |
| Create | `frontend/components/workbench/trim-interpretation/index.ts` | Barrel exports |
| Modify | `frontend/hooks/useOperatingPoints.ts` | Add `aero_coefficients` to `TrimEnrichment` type |
| Modify | `frontend/components/workbench/OperatingPointsPanel.tsx` | Replace inline enrichment components with new imports, add comparison tab |
| Modify | `app/schemas/aeroanalysisschema.py` | Add `aero_coefficients` field to `TrimEnrichment` |
| Modify | `app/services/trim_enrichment_service.py` | Pass `aero_coefficients` through to return value |
| Create | `frontend/__tests__/trim-interpretation/AnalysisGoalCard.test.tsx` | Unit tests |
| Create | `frontend/__tests__/trim-interpretation/ControlAuthorityChart.test.tsx` | Unit tests |
| Create | `frontend/__tests__/trim-interpretation/DesignWarningBadges.test.tsx` | Unit tests |
| Create | `frontend/__tests__/trim-interpretation/MixerValuesCard.test.tsx` | Unit tests |
| Create | `frontend/__tests__/trim-interpretation/OpComparisonTable.test.tsx` | Unit tests |
| Create | `frontend/e2e/features/trim-interpretation.feature` | E2E spec |

---

### Task 1: Backend — Add `aero_coefficients` to TrimEnrichment

**Files:**
- Modify: `app/schemas/aeroanalysisschema.py:463` (TrimEnrichment class)
- Modify: `app/services/trim_enrichment_service.py:463` (compute_enrichment return)
- Test: `app/tests/test_trim_enrichment.py`

- [ ] **Step 1: Write failing test**

```python
# Add to app/tests/test_trim_enrichment.py, in TestTrimEnrichment class:

def test_aero_coefficients_field(self):
    """TrimEnrichment stores aero coefficients when provided."""
    enrichment = TrimEnrichment(
        analysis_goal="Test",
        trim_method="opti",
        trim_score=0.01,
        trim_residuals={},
        deflection_reserves={},
        design_warnings=[],
        effectiveness={},
        stability_classification=None,
        mixer_values={},
        result_summary="Test",
        aero_coefficients={"CL": 0.45, "CD": 0.032, "Cm": -0.001},
    )
    assert enrichment.aero_coefficients == {"CL": 0.45, "CD": 0.032, "Cm": -0.001}

def test_aero_coefficients_defaults_empty(self):
    """TrimEnrichment.aero_coefficients defaults to empty dict."""
    enrichment = TrimEnrichment(
        analysis_goal="Test",
        trim_method="opti",
        trim_score=None,
        trim_residuals={},
        deflection_reserves={},
        design_warnings=[],
        effectiveness={},
        stability_classification=None,
        mixer_values={},
        result_summary="",
    )
    assert enrichment.aero_coefficients == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_trim_enrichment.py::TestTrimEnrichment::test_aero_coefficients_field -v`
Expected: FAIL — `unexpected keyword argument 'aero_coefficients'`

- [ ] **Step 3: Add the field to TrimEnrichment schema**

In `app/schemas/aeroanalysisschema.py`, add after the `result_summary` field:

```python
    aero_coefficients: dict[str, float] = Field(
        default_factory=dict, description="Aerodynamic coefficients at trim (CL, CD, Cm, etc.)"
    )
```

- [ ] **Step 4: Pass aero_coefficients through in compute_enrichment**

In `app/services/trim_enrichment_service.py`, update the `return TrimEnrichment(...)` at line 463 to include:

```python
    return TrimEnrichment(
        analysis_goal=analysis_goal,
        trim_method=trim_method,
        trim_score=trim_score,
        trim_residuals=trim_residuals,
        deflection_reserves=deflection_reserves,
        design_warnings=warnings,
        effectiveness=effectiveness,
        stability_classification=stability_classification,
        mixer_values=mixer_values,
        result_summary=result_summary,
        aero_coefficients=aero_coefficients or {},
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/schemas/aeroanalysisschema.py app/services/trim_enrichment_service.py app/tests/test_trim_enrichment.py
git commit -m "feat(gh-452): add aero_coefficients field to TrimEnrichment schema"
```

---

### Task 2: Frontend Types — Update TrimEnrichment interface

**Files:**
- Modify: `frontend/hooks/useOperatingPoints.ts`
- Test: `frontend/__tests__/trim-enrichment-types.test.ts`

- [ ] **Step 1: Write failing type test**

```typescript
// frontend/__tests__/trim-enrichment-types.test.ts
import { describe, it, expectTypeOf } from "vitest";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

describe("TrimEnrichment type", () => {
  it("includes aero_coefficients field", () => {
    expectTypeOf<TrimEnrichment>().toHaveProperty("aero_coefficients");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-enrichment-types.test.ts`
Expected: FAIL — property `aero_coefficients` does not exist

- [ ] **Step 3: Add aero_coefficients to TrimEnrichment interface**

In `frontend/hooks/useOperatingPoints.ts`, add to the `TrimEnrichment` interface:

```typescript
export interface TrimEnrichment {
  analysis_goal: string;
  result_summary: string;
  trim_method: string;
  trim_score: number | null;
  trim_residuals: Record<string, number>;
  deflection_reserves: Record<string, DeflectionReserve>;
  design_warnings: DesignWarning[];
  effectiveness: Record<string, ControlEffectiveness>;
  stability_classification: StabilityClassification | null;
  mixer_values: Record<string, MixerValues>;
  aero_coefficients: Record<string, number>;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-enrichment-types.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useOperatingPoints.ts frontend/__tests__/trim-enrichment-types.test.ts
git commit -m "feat(gh-452): update TrimEnrichment TS types with all enrichment fields"
```

---

### Task 3: AnalysisGoalCard — Goal + Summary + Status Badge

**Files:**
- Create: `frontend/components/workbench/trim-interpretation/AnalysisGoalCard.tsx`
- Create: `frontend/__tests__/trim-interpretation/AnalysisGoalCard.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/trim-interpretation/AnalysisGoalCard.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalysisGoalCard } from "@/components/workbench/trim-interpretation/AnalysisGoalCard";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Can the aircraft trim near stall?",
  result_summary: "Trimmed at α=12.3° with 82% elevator reserve",
  trim_method: "opti",
  trim_score: 0.02,
  trim_residuals: { cm: 0.001 },
  deflection_reserves: {
    "[elevator]Elevator": {
      deflection_deg: -5.0,
      max_pos_deg: 25.0,
      max_neg_deg: 25.0,
      usage_fraction: 0.18,
    },
  },
  design_warnings: [],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: { CL: 1.2, CD: 0.06 },
};

describe("AnalysisGoalCard", () => {
  it("renders analysis goal and result summary", () => {
    render(<AnalysisGoalCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Can the aircraft trim near stall?")).toBeTruthy();
    expect(screen.getByText("Trimmed at α=12.3° with 82% elevator reserve")).toBeTruthy();
  });

  it("shows green badge when all reserves below 60%", () => {
    render(<AnalysisGoalCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-emerald-500");
  });

  it("shows amber badge when any reserve between 60-80%", () => {
    const amber = {
      ...MOCK_ENRICHMENT,
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -17.0,
          max_pos_deg: 25.0,
          max_neg_deg: 25.0,
          usage_fraction: 0.68,
        },
      },
    };
    render(<AnalysisGoalCard enrichment={amber} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-amber-500");
  });

  it("shows red badge when any reserve above 80%", () => {
    const red = {
      ...MOCK_ENRICHMENT,
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -22.0,
          max_pos_deg: 25.0,
          max_neg_deg: 25.0,
          usage_fraction: 0.88,
        },
      },
    };
    render(<AnalysisGoalCard enrichment={red} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-red-500");
  });

  it("shows red badge when design_warnings contain critical level", () => {
    const critical = {
      ...MOCK_ENRICHMENT,
      design_warnings: [
        { level: "critical" as const, category: "authority", surface: null, message: "Near limit" },
      ],
    };
    render(<AnalysisGoalCard enrichment={critical} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-red-500");
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<AnalysisGoalCard enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/AnalysisGoalCard.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement AnalysisGoalCard**

```typescript
// frontend/components/workbench/trim-interpretation/AnalysisGoalCard.tsx
"use client";

import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

function computeStatusLevel(enrichment: TrimEnrichment): "healthy" | "marginal" | "critical" {
  if (enrichment.design_warnings.some((w) => w.level === "critical")) return "critical";
  const maxUsage = Math.max(
    0,
    ...Object.values(enrichment.deflection_reserves).map((r) => r.usage_fraction),
  );
  if (maxUsage > 0.8) return "critical";
  if (maxUsage > 0.6) return "marginal";
  if (enrichment.design_warnings.some((w) => w.level === "warning")) return "marginal";
  return "healthy";
}

const BADGE_STYLES = {
  healthy: "bg-emerald-500",
  marginal: "bg-amber-500",
  critical: "bg-red-500",
} as const;

const BADGE_LABELS = {
  healthy: "Healthy",
  marginal: "Marginal",
  critical: "Critical",
} as const;

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function AnalysisGoalCard({ enrichment }: Props) {
  if (!enrichment) return null;

  const level = computeStatusLevel(enrichment);

  return (
    <div className="rounded-lg border border-[#FF8400]/30 bg-[#FF8400]/10 px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-[#FF8400]">
          Analysis Goal
        </span>
        <span
          data-testid="status-badge"
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold text-white ${BADGE_STYLES[level]}`}
        >
          {BADGE_LABELS[level]}
        </span>
      </div>
      <p className="mt-1 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
        {enrichment.analysis_goal}
      </p>
      {enrichment.result_summary && (
        <p className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {enrichment.result_summary}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/AnalysisGoalCard.test.tsx`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/trim-interpretation/AnalysisGoalCard.tsx frontend/__tests__/trim-interpretation/AnalysisGoalCard.test.tsx
git commit -m "feat(gh-452): add AnalysisGoalCard with status badge"
```

---

### Task 4: ControlAuthorityChart — Plotly Horizontal Bar Chart

**Files:**
- Create: `frontend/components/workbench/trim-interpretation/ControlAuthorityChart.tsx`
- Create: `frontend/__tests__/trim-interpretation/ControlAuthorityChart.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/trim-interpretation/ControlAuthorityChart.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ControlAuthorityChart } from "@/components/workbench/trim-interpretation/ControlAuthorityChart";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

// Mock Plotly — it's dynamically imported and we can't render canvas in jsdom
vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Test",
  result_summary: "",
  trim_method: "opti",
  trim_score: 0.01,
  trim_residuals: {},
  deflection_reserves: {
    "[elevator]Elevator": {
      deflection_deg: -5.0,
      max_pos_deg: 25.0,
      max_neg_deg: 25.0,
      usage_fraction: 0.2,
    },
    "[aileron]Left Aileron": {
      deflection_deg: 3.0,
      max_pos_deg: 20.0,
      max_neg_deg: 20.0,
      usage_fraction: 0.15,
    },
    "[aileron]Right Aileron": {
      deflection_deg: -3.0,
      max_pos_deg: 20.0,
      max_neg_deg: 20.0,
      usage_fraction: 0.15,
    },
  },
  design_warnings: [],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: {},
};

describe("ControlAuthorityChart", () => {
  it("renders chart container with correct heading", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Control Authority")).toBeTruthy();
  });

  it("renders a chart container div", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByTestId("authority-chart-container")).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<ControlAuthorityChart enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when no deflection reserves", () => {
    const empty = { ...MOCK_ENRICHMENT, deflection_reserves: {} };
    const { container } = render(<ControlAuthorityChart enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/ControlAuthorityChart.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement ControlAuthorityChart**

```typescript
// frontend/components/workbench/trim-interpretation/ControlAuthorityChart.tsx
"use client";

import { useRef, useEffect } from "react";
import type { TrimEnrichment, DeflectionReserve } from "@/hooks/useOperatingPoints";

function authorityColor(fraction: number): string {
  if (fraction > 0.8) return "#EF4444";
  if (fraction > 0.6) return "#F59E0B";
  return "#30A46C";
}

function displaySurfaceName(encoded: string): string {
  const match = encoded.match(/^\[(\w+)\](.+)$/);
  return match ? match[2] : encoded;
}

function formatLabel(name: string, reserve: DeflectionReserve): string {
  const displayName = displaySurfaceName(name);
  const limit = reserve.deflection_deg >= 0 ? reserve.max_pos_deg : reserve.max_neg_deg;
  const reservePct = Math.round((1 - reserve.usage_fraction) * 100);
  return `${displayName}: ${reserve.deflection_deg.toFixed(1)}° / ±${limit.toFixed(0)}° (${reservePct}% reserve)`;
}

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function ControlAuthorityChart({ enrichment }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || !enrichment) return;

    const entries = Object.entries(enrichment.deflection_reserves);
    if (entries.length === 0) return;

    let disposed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const surfaceNames = entries.map(([name]) => displaySurfaceName(name));
      const usagePcts = entries.map(([, r]) => Math.round(r.usage_fraction * 100));
      const colors = entries.map(([, r]) => authorityColor(r.usage_fraction));
      const hoverTexts = entries.map(([name, r]) => formatLabel(name, r));

      const trace = {
        type: "bar",
        orientation: "h",
        y: surfaceNames,
        x: usagePcts,
        marker: { color: colors },
        text: usagePcts.map((p) => `${p}%`),
        textposition: "outside",
        textfont: { color: "#A1A1AA", size: 11, family: "JetBrains Mono" },
        hovertext: hoverTexts,
        hoverinfo: "text",
      };

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", size: 11, family: "JetBrains Mono" },
        margin: { l: 120, r: 50, t: 10, b: 30 },
        xaxis: {
          range: [0, 110],
          dtick: 25,
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
          title: { text: "Authority Used (%)", font: { size: 10 } },
        },
        yaxis: {
          automargin: true,
          tickfont: { size: 11 },
        },
        shapes: [
          {
            type: "line",
            x0: 80,
            x1: 80,
            y0: -0.5,
            y1: entries.length - 0.5,
            line: { color: "#F59E0B", width: 1, dash: "dot" },
          },
        ],
        height: Math.max(120, entries.length * 40 + 50),
        autosize: true,
      };

      await PlotlyRef.react(node, [trace], layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [enrichment]);

  if (!enrichment || Object.keys(enrichment.deflection_reserves).length === 0) return null;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        Control Authority
      </span>
      <div ref={containerRef} data-testid="authority-chart-container" className="min-h-[120px]" />
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/ControlAuthorityChart.test.tsx`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/trim-interpretation/ControlAuthorityChart.tsx frontend/__tests__/trim-interpretation/ControlAuthorityChart.test.tsx
git commit -m "feat(gh-452): add Plotly-based ControlAuthorityChart"
```

---

### Task 5: DesignWarningBadges — Expandable Warnings

**Files:**
- Create: `frontend/components/workbench/trim-interpretation/DesignWarningBadges.tsx`
- Create: `frontend/__tests__/trim-interpretation/DesignWarningBadges.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/trim-interpretation/DesignWarningBadges.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DesignWarningBadges } from "@/components/workbench/trim-interpretation/DesignWarningBadges";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Test",
  result_summary: "",
  trim_method: "opti",
  trim_score: null,
  trim_residuals: {},
  deflection_reserves: {},
  design_warnings: [
    {
      level: "critical",
      category: "authority",
      surface: "[elevator]Elevator",
      message: "Elevator near mechanical limit (96% used)",
    },
    {
      level: "warning",
      category: "authority",
      surface: "[aileron]Left Aileron",
      message: "75% authority used — surface may be undersized",
    },
    {
      level: "info",
      category: "stability",
      surface: null,
      message: "Large static margin — nose-heavy tendency",
    },
  ],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: {},
};

describe("DesignWarningBadges", () => {
  it("renders all warning messages", () => {
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/Elevator near mechanical limit/)).toBeTruthy();
    expect(screen.getByText(/75% authority used/)).toBeTruthy();
    expect(screen.getByText(/Large static margin/)).toBeTruthy();
  });

  it("expands badge on click to show details", async () => {
    const user = userEvent.setup();
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    const badge = screen.getByText(/Elevator near mechanical limit/);
    await user.click(badge);
    expect(screen.getByText(/authority/i)).toBeTruthy();
    expect(screen.getByText(/Elevator/)).toBeTruthy();
  });

  it("collapses expanded badge on second click", async () => {
    const user = userEvent.setup();
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    const badge = screen.getByText(/Elevator near mechanical limit/);
    await user.click(badge);
    expect(screen.getByTestId("warning-detail-0")).toBeTruthy();
    await user.click(badge);
    expect(screen.queryByTestId("warning-detail-0")).toBeNull();
  });

  it("renders nothing when no warnings", () => {
    const empty = { ...MOCK_ENRICHMENT, design_warnings: [] };
    const { container } = render(<DesignWarningBadges enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<DesignWarningBadges enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("applies correct color for each severity level", () => {
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    const badges = screen.getAllByRole("button");
    expect(badges[0].className).toContain("red");
    expect(badges[1].className).toContain("yellow");
    expect(badges[2].className).toContain("blue");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/DesignWarningBadges.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement DesignWarningBadges**

```typescript
// frontend/components/workbench/trim-interpretation/DesignWarningBadges.tsx
"use client";

import { useState } from "react";
import type { TrimEnrichment, DesignWarning } from "@/hooks/useOperatingPoints";

const WARNING_STYLES = {
  info: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  warning: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  critical: "border-red-500/30 bg-red-500/10 text-red-400",
} as const;

const DETAIL_BG = {
  info: "bg-blue-500/5",
  warning: "bg-yellow-500/5",
  critical: "bg-red-500/5",
} as const;

function displaySurfaceName(encoded: string): string {
  const match = encoded.match(/^\[(\w+)\](.+)$/);
  return match ? match[2] : encoded;
}

function WarningBadge({
  warning,
  index,
  isExpanded,
  onToggle,
}: {
  warning: DesignWarning;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex flex-col">
      <button
        type="button"
        onClick={onToggle}
        className={`cursor-pointer rounded-lg border px-3 py-2 text-left transition-all ${WARNING_STYLES[warning.level] ?? WARNING_STYLES.info}`}
      >
        <span className="font-[family-name:var(--font-geist-sans)] text-[12px]">
          {warning.message}
        </span>
      </button>
      {isExpanded && (
        <div
          data-testid={`warning-detail-${index}`}
          className={`mt-1 rounded-b-lg px-3 py-2 ${DETAIL_BG[warning.level] ?? DETAIL_BG.info}`}
        >
          <dl className="flex flex-col gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            <div className="flex gap-2">
              <dt className="font-medium">Category:</dt>
              <dd>{warning.category}</dd>
            </div>
            {warning.surface && (
              <div className="flex gap-2">
                <dt className="font-medium">Surface:</dt>
                <dd>{displaySurfaceName(warning.surface)}</dd>
              </div>
            )}
            <div className="flex gap-2">
              <dt className="font-medium">Severity:</dt>
              <dd className="capitalize">{warning.level}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function DesignWarningBadges({ enrichment }: Props) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!enrichment || enrichment.design_warnings.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5">
      {enrichment.design_warnings.map((w, i) => (
        <WarningBadge
          key={i}
          warning={w}
          index={i}
          isExpanded={expandedIndex === i}
          onToggle={() => setExpandedIndex(expandedIndex === i ? null : i)}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/DesignWarningBadges.test.tsx`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/trim-interpretation/DesignWarningBadges.tsx frontend/__tests__/trim-interpretation/DesignWarningBadges.test.tsx
git commit -m "feat(gh-452): add expandable DesignWarningBadges component"
```

---

### Task 6: MixerValuesCard — Dual-Role Surface Display

**Files:**
- Create: `frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx`
- Create: `frontend/__tests__/trim-interpretation/MixerValuesCard.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/trim-interpretation/MixerValuesCard.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MixerValuesCard } from "@/components/workbench/trim-interpretation/MixerValuesCard";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Test",
  result_summary: "",
  trim_method: "opti",
  trim_score: null,
  trim_residuals: {},
  deflection_reserves: {},
  design_warnings: [],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {
    elevon: {
      symmetric_offset: 3.2,
      differential_throw: 5.1,
      role: "elevon",
    },
    flaperon: {
      symmetric_offset: -1.5,
      differential_throw: 8.0,
      role: "flaperon",
    },
  },
  aero_coefficients: {},
};

describe("MixerValuesCard", () => {
  it("renders mixer heading", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Mixer Setup")).toBeTruthy();
  });

  it("renders symmetric offset for each mixer group", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("3.2°")).toBeTruthy();
    expect(screen.getByText("-1.5°")).toBeTruthy();
  });

  it("renders differential throw for each mixer group", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("5.1°")).toBeTruthy();
    expect(screen.getByText("8.0°")).toBeTruthy();
  });

  it("renders role labels", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/elevon/i)).toBeTruthy();
    expect(screen.getByText(/flaperon/i)).toBeTruthy();
  });

  it("renders nothing when no mixer values", () => {
    const empty = { ...MOCK_ENRICHMENT, mixer_values: {} };
    const { container } = render(<MixerValuesCard enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<MixerValuesCard enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/MixerValuesCard.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement MixerValuesCard**

```typescript
// frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx
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
                  {mixer.symmetric_offset.toFixed(1)}°
                </span>
              </div>
              <div className="flex flex-col">
                <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                  Differential Throw
                </span>
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                  {mixer.differential_throw.toFixed(1)}°
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/MixerValuesCard.test.tsx`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/trim-interpretation/MixerValuesCard.tsx frontend/__tests__/trim-interpretation/MixerValuesCard.test.tsx
git commit -m "feat(gh-452): add MixerValuesCard for dual-role surfaces"
```

---

### Task 7: OpComparisonTable — Multi-OP Comparison

**Files:**
- Create: `frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx`
- Create: `frontend/__tests__/trim-interpretation/OpComparisonTable.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/trim-interpretation/OpComparisonTable.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OpComparisonTable } from "@/components/workbench/trim-interpretation/OpComparisonTable";
import type { StoredOperatingPoint } from "@/hooks/useOperatingPoints";

const RAD = Math.PI / 180;

function makeOp(overrides: Partial<StoredOperatingPoint> & { name: string }): StoredOperatingPoint {
  return {
    id: 1,
    description: "",
    aircraft_id: 1,
    config: "clean",
    status: "TRIMMED",
    warnings: [],
    controls: {},
    velocity: 15,
    alpha: 5 * RAD,
    beta: 0,
    p: 0,
    q: 0,
    r: 0,
    xyz_ref: [0, 0, 0],
    altitude: 0,
    control_deflections: null,
    trim_enrichment: null,
    ...overrides,
  };
}

const POINTS: StoredOperatingPoint[] = [
  makeOp({
    id: 1,
    name: "cruise",
    alpha: 3 * RAD,
    trim_enrichment: {
      analysis_goal: "Cruise trim",
      result_summary: "",
      trim_method: "opti",
      trim_score: 0.01,
      trim_residuals: {},
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -2.5,
          max_pos_deg: 25,
          max_neg_deg: 25,
          usage_fraction: 0.1,
        },
      },
      design_warnings: [],
      effectiveness: {},
      stability_classification: null,
      mixer_values: {},
      aero_coefficients: { CL: 0.45, CD: 0.032 },
    },
  }),
  makeOp({
    id: 2,
    name: "stall_approach",
    alpha: 12 * RAD,
    trim_enrichment: {
      analysis_goal: "Near stall",
      result_summary: "",
      trim_method: "opti",
      trim_score: 0.05,
      trim_residuals: {},
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -20.0,
          max_pos_deg: 25,
          max_neg_deg: 25,
          usage_fraction: 0.8,
        },
      },
      design_warnings: [],
      effectiveness: {},
      stability_classification: null,
      mixer_values: {},
      aero_coefficients: { CL: 1.3, CD: 0.09 },
    },
  }),
  makeOp({
    id: 3,
    name: "untrimmed",
    status: "NOT_TRIMMED",
    trim_enrichment: null,
  }),
];

describe("OpComparisonTable", () => {
  it("renders table headers", () => {
    render(<OpComparisonTable points={POINTS} />);
    expect(screen.getByText("OP")).toBeTruthy();
    expect(screen.getByText("α (°)")).toBeTruthy();
    expect(screen.getByText("Elev (°)")).toBeTruthy();
    expect(screen.getByText("Reserve")).toBeTruthy();
    expect(screen.getByText("CL")).toBeTruthy();
    expect(screen.getByText("CD")).toBeTruthy();
    expect(screen.getByText("L/D")).toBeTruthy();
  });

  it("only renders trimmed OPs with enrichment", () => {
    render(<OpComparisonTable points={POINTS} />);
    expect(screen.getByText("cruise")).toBeTruthy();
    expect(screen.getByText("stall_approach")).toBeTruthy();
    expect(screen.queryByText("untrimmed")).toBeNull();
  });

  it("computes L/D from CL and CD", () => {
    render(<OpComparisonTable points={POINTS} />);
    // cruise: CL=0.45 / CD=0.032 = 14.1
    expect(screen.getByText("14.1")).toBeTruthy();
  });

  it("highlights worst-case row (highest usage_fraction)", () => {
    render(<OpComparisonTable points={POINTS} />);
    const worstRow = screen.getByTestId("op-row-2");
    expect(worstRow.className).toContain("red");
  });

  it("sorts by column on header click", async () => {
    const user = userEvent.setup();
    render(<OpComparisonTable points={POINTS} />);
    const alphaHeader = screen.getByText("α (°)");
    await user.click(alphaHeader);
    const rows = screen.getAllByTestId(/^op-row-/);
    expect(rows).toHaveLength(2);
  });

  it("renders nothing when no trimmed points exist", () => {
    const untrimmed = [makeOp({ name: "x", status: "NOT_TRIMMED" })];
    const { container } = render(<OpComparisonTable points={untrimmed} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/OpComparisonTable.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement OpComparisonTable**

```typescript
// frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx
"use client";

import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import type { StoredOperatingPoint } from "@/hooks/useOperatingPoints";

const RAD_TO_DEG = 180 / Math.PI;

type SortKey = "name" | "alpha" | "elevator" | "reserve" | "cl" | "cd" | "ld";
type SortDir = "asc" | "desc";

interface RowData {
  id: number;
  name: string;
  alpha_deg: number;
  elevator_deg: number | null;
  reserve_pct: number;
  cl: number | null;
  cd: number | null;
  ld: number | null;
}

function extractElevator(enrichment: NonNullable<StoredOperatingPoint["trim_enrichment"]>): {
  deg: number | null;
  reserve: number;
} {
  const elevatorEntry = Object.entries(enrichment.deflection_reserves).find(([key]) =>
    key.toLowerCase().includes("elevator"),
  );
  if (!elevatorEntry) {
    const firstEntry = Object.entries(enrichment.deflection_reserves)[0];
    if (!firstEntry) return { deg: null, reserve: 0 };
    return { deg: firstEntry[1].deflection_deg, reserve: firstEntry[1].usage_fraction };
  }
  return { deg: elevatorEntry[1].deflection_deg, reserve: elevatorEntry[1].usage_fraction };
}

function computeMaxReserve(enrichment: NonNullable<StoredOperatingPoint["trim_enrichment"]>): number {
  return Math.max(0, ...Object.values(enrichment.deflection_reserves).map((r) => r.usage_fraction));
}

interface Props {
  readonly points: StoredOperatingPoint[];
}

export function OpComparisonTable({ points }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("reserve");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const rows: RowData[] = useMemo(() => {
    return points
      .filter((p) => p.status === "TRIMMED" && p.trim_enrichment)
      .map((p) => {
        const enrichment = p.trim_enrichment!;
        const { deg, reserve } = extractElevator(enrichment);
        const cl = enrichment.aero_coefficients?.CL ?? null;
        const cd = enrichment.aero_coefficients?.CD ?? null;
        const ld = cl !== null && cd !== null && cd > 0 ? cl / cd : null;
        return {
          id: p.id,
          name: p.name,
          alpha_deg: p.alpha * RAD_TO_DEG,
          elevator_deg: deg,
          reserve_pct: Math.round(reserve * 100),
          cl,
          cd,
          ld,
        };
      });
  }, [points]);

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.name.localeCompare(b.name);
          break;
        case "alpha":
          cmp = a.alpha_deg - b.alpha_deg;
          break;
        case "elevator":
          cmp = (a.elevator_deg ?? 0) - (b.elevator_deg ?? 0);
          break;
        case "reserve":
          cmp = a.reserve_pct - b.reserve_pct;
          break;
        case "cl":
          cmp = (a.cl ?? 0) - (b.cl ?? 0);
          break;
        case "cd":
          cmp = (a.cd ?? 0) - (b.cd ?? 0);
          break;
        case "ld":
          cmp = (a.ld ?? 0) - (b.ld ?? 0);
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const worstId = useMemo(() => {
    if (rows.length === 0) return null;
    return rows.reduce((worst, r) => (r.reserve_pct > worst.reserve_pct ? r : worst), rows[0]).id;
  }, [rows]);

  if (rows.length === 0) return null;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "OP" },
    { key: "alpha", label: "α (°)" },
    { key: "elevator", label: "Elev (°)" },
    { key: "reserve", label: "Reserve" },
    { key: "cl", label: "CL" },
    { key: "cd", label: "CD" },
    { key: "ld", label: "L/D" },
  ];

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        OP Comparison
      </span>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-[family-name:var(--font-jetbrains-mono)] text-[11px]">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer px-2 py-1.5 text-muted-foreground hover:text-foreground"
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {sortKey === col.key &&
                      (sortDir === "asc" ? (
                        <ChevronUp className="h-3 w-3" />
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      ))}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr
                key={row.id}
                data-testid={`op-row-${row.id}`}
                className={`border-b border-border/50 ${
                  row.id === worstId ? "bg-red-500/10 text-red-400" : "text-foreground"
                }`}
              >
                <td className="px-2 py-1.5 font-medium">{row.name}</td>
                <td className="px-2 py-1.5">{row.alpha_deg.toFixed(1)}</td>
                <td className="px-2 py-1.5">
                  {row.elevator_deg !== null ? row.elevator_deg.toFixed(1) : "—"}
                </td>
                <td className="px-2 py-1.5">{row.reserve_pct}%</td>
                <td className="px-2 py-1.5">{row.cl !== null ? row.cl.toFixed(3) : "—"}</td>
                <td className="px-2 py-1.5">{row.cd !== null ? row.cd.toFixed(4) : "—"}</td>
                <td className="px-2 py-1.5">{row.ld !== null ? row.ld.toFixed(1) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run __tests__/trim-interpretation/OpComparisonTable.test.tsx`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx frontend/__tests__/trim-interpretation/OpComparisonTable.test.tsx
git commit -m "feat(gh-452): add OpComparisonTable with sorting and worst-case highlighting"
```

---

### Task 8: Barrel Export + Integration into OperatingPointsPanel

**Files:**
- Create: `frontend/components/workbench/trim-interpretation/index.ts`
- Modify: `frontend/components/workbench/OperatingPointsPanel.tsx`
- Modify: `frontend/__tests__/operating-points-enrichment.test.tsx`

- [ ] **Step 1: Create barrel export**

```typescript
// frontend/components/workbench/trim-interpretation/index.ts
export { AnalysisGoalCard } from "./AnalysisGoalCard";
export { ControlAuthorityChart } from "./ControlAuthorityChart";
export { DesignWarningBadges } from "./DesignWarningBadges";
export { MixerValuesCard } from "./MixerValuesCard";
export { OpComparisonTable } from "./OpComparisonTable";
```

- [ ] **Step 2: Update OperatingPointsPanel imports and drawer section**

In `frontend/components/workbench/OperatingPointsPanel.tsx`:

Replace the imports at the top — remove the `TrimEnrichment` import from types used only by the old inline components (keep it for the type annotation). Add new imports:

```typescript
import {
  AnalysisGoalCard,
  ControlAuthorityChart,
  DesignWarningBadges,
  MixerValuesCard,
  OpComparisonTable,
} from "./trim-interpretation";
```

Replace lines 375-377 (the old inline component calls) with:

```typescript
              <AnalysisGoalCard enrichment={selectedPoint.trim_enrichment ?? null} />
              <ControlAuthorityChart enrichment={selectedPoint.trim_enrichment ?? null} />
              <DesignWarningBadges enrichment={selectedPoint.trim_enrichment ?? null} />
              <MixerValuesCard enrichment={selectedPoint.trim_enrichment ?? null} />
```

Add the OpComparisonTable OUTSIDE the drawer (in the main panel area, after the table or as a collapsible section below it). Find the end of the main table section and add:

```typescript
      <OpComparisonTable points={sortedPoints} />
```

- [ ] **Step 3: Remove old inline components**

Delete the old `AnalysisGoalBanner`, `ControlAuthorityChart`, `DesignWarningBadges`, `authorityColor`, `displaySurfaceName`, and `WARNING_STYLES` from the bottom of `OperatingPointsPanel.tsx` (lines 810-898).

- [ ] **Step 4: Update existing test imports**

In `frontend/__tests__/operating-points-enrichment.test.tsx`, update imports to point to new locations:

```typescript
import {
  AnalysisGoalCard,
  ControlAuthorityChart,
  DesignWarningBadges,
} from "@/components/workbench/trim-interpretation";
```

Update the test to use `AnalysisGoalCard` instead of `AnalysisGoalBanner`, and update mock data to include new required fields (`result_summary`, `effectiveness`, `stability_classification`, `mixer_values`, `aero_coefficients`).

- [ ] **Step 5: Run all unit tests**

Run: `cd frontend && npm run test:unit -- --run`
Expected: ALL PASS (existing + new tests)

- [ ] **Step 6: Commit**

```bash
git add frontend/components/workbench/trim-interpretation/index.ts frontend/components/workbench/OperatingPointsPanel.tsx frontend/__tests__/operating-points-enrichment.test.tsx
git commit -m "feat(gh-452): integrate trim interpretation components into OP drawer"
```

---

### Task 9: E2E Feature Specification

**Files:**
- Create: `frontend/e2e/features/trim-interpretation.feature`

- [ ] **Step 1: Write the Playwright-BDD feature**

```gherkin
# frontend/e2e/features/trim-interpretation.feature
Feature: Trim Interpretation UI

  Background:
    Given an aeroplane "IntegrationTest" with a main wing and elevator
    And design assumptions are seeded with mass 1.5 kg and CL_max 1.4
    And operating points are generated and trimmed

  Scenario: View analysis goal card with status badge
    When I click on the "cruise" operating point row
    Then the detail drawer opens
    And the analysis goal card shows "Analysis Goal"
    And the analysis goal card has a status badge

  Scenario: View control authority chart
    When I click on the "cruise" operating point row
    Then the detail drawer opens
    And the control authority chart is visible
    And the chart shows at least one surface bar

  Scenario: Expand design warning for details
    Given the "stall_approach" OP has a critical warning
    When I click on the "stall_approach" operating point row
    Then the detail drawer opens
    And warning badges are displayed
    When I click on the first warning badge
    Then warning details are expanded showing category and severity

  Scenario: View mixer values for dual-role surfaces
    Given the aircraft has elevon surfaces
    When I click on a trimmed operating point row
    Then the mixer setup card shows symmetric offset and differential throw

  Scenario: Compare trim results across operating points
    Then the OP comparison table is visible
    And the table shows columns for OP name, alpha, elevator, reserve, CL, CD, L/D
    And the worst-case row is highlighted in red
    When I click the "α (°)" column header
    Then the table rows are sorted by alpha
```

- [ ] **Step 2: Commit**

```bash
git add frontend/e2e/features/trim-interpretation.feature
git commit -m "test(gh-452): add E2E feature specification for trim interpretation UI"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] Analysis goal + result summary + status badge → Task 3
   - [x] Control authority bar chart (Plotly, color-coded) → Task 4
   - [x] Design warning badges (click-to-expand) → Task 5
   - [x] Mixer values card → Task 6
   - [x] Multi-OP comparison table (sortable, worst-case) → Task 7
   - [x] Integration into existing drawer → Task 8
   - [x] Vitest unit tests → Tasks 3-7
   - [x] E2E playwright-bdd → Task 9
   - [x] Backend data for CL/CD/L÷D → Task 1

2. **Placeholder scan:** No TBD/TODO found. All code blocks are complete.

3. **Type consistency:** `TrimEnrichment` interface matches across all tasks. `enrichment` prop signature is consistent (`TrimEnrichment | null`). `StoredOperatingPoint` used correctly in Task 7. `DeflectionReserve` field names match backend schema.
