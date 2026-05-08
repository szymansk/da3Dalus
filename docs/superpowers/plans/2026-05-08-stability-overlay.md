# Stability Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Stability" tab to the Analysis page showing a 2D side-view schematic with NP, CG, CG range, and static margin markers.

**Architecture:** Frontend-only feature. New `useStability` hook fetches from existing `GET /v2/aeroplanes/{id}/stability` endpoint. `StabilityPanel` container renders `StabilitySideView` (Plotly 2D) and `MarkerDetailBox` (click popup). Tab integrated into existing `AnalysisViewerPanel`.

**Tech Stack:** React 19, TypeScript, Plotly.js (dynamic import via `plotly.js-gl3d-dist-min`), Vitest + React Testing Library

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/hooks/useStability.ts` | Fetch/compute stability data |
| Create | `frontend/__tests__/useStability.test.ts` | Hook tests |
| Create | `frontend/components/workbench/StabilityPanel.tsx` | Container: toolbar, states, layout |
| Create | `frontend/__tests__/StabilityPanel.test.tsx` | Panel rendering tests |
| Create | `frontend/components/workbench/StabilitySideView.tsx` | Plotly 2D schematic with markers |
| Create | `frontend/__tests__/StabilitySideView.test.tsx` | Side-view rendering tests |
| Create | `frontend/components/workbench/MarkerDetailBox.tsx` | Click-detail popup |
| Create | `frontend/__tests__/MarkerDetailBox.test.tsx` | Detail box tests |
| Modify | `frontend/components/workbench/AnalysisViewerPanel.tsx` | Add "Stability" tab |
| Modify | `frontend/app/workbench/analysis/page.tsx` | Wire useStability hook |

---

### Task 1: useStability Hook

**Files:**
- Create: `frontend/hooks/useStability.ts`
- Create: `frontend/__tests__/useStability.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/useStability.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useStability, type StabilityData } from "@/hooks/useStability";

const FAKE_STABILITY: StabilityData = {
  id: 1,
  aeroplane_id: 42,
  solver: "avl",
  neutral_point_x: 0.25,
  mac: 0.15,
  cg_x_used: 0.20,
  static_margin_pct: 33.3,
  stability_class: "stable",
  cg_range_forward: 0.17,
  cg_range_aft: 0.24,
  Cma: -1.2,
  Cnb: 0.05,
  Clb: -0.03,
  is_statically_stable: true,
  is_directionally_stable: true,
  is_laterally_stable: true,
  trim_alpha_deg: 2.5,
  trim_elevator_deg: -3.0,
  computed_at: "2026-05-08T12:00:00Z",
  status: "CURRENT",
  geometry_hash: "abc123",
};

describe("useStability", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null data when aeroplaneId is null", () => {
    const { result } = renderHook(() => useStability(null));
    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isComputing).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("fetches stability data on mount", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_STABILITY),
    });

    const { result } = renderHook(() => useStability("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/aeroplanes/42/stability"),
    );
    expect(result.current.data).toEqual(FAKE_STABILITY);
    expect(result.current.error).toBeNull();
  });

  it("handles 404 by setting data to null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    });

    const { result } = renderHook(() => useStability("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("sets error on non-404 fetch failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal server error"),
    });

    const { result } = renderHook(() => useStability("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toContain("500");
  });

  it("compute() POSTs to stability_summary and refreshes cached data", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve("Not found"),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(FAKE_STABILITY),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(FAKE_STABILITY),
      });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useStability("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.compute();
    });

    expect(mockFetch.mock.calls[1][0]).toContain(
      "/aeroplanes/42/stability_summary/avl",
    );
    expect(mockFetch.mock.calls[1][1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.current.data).toEqual(FAKE_STABILITY);
    expect(result.current.isComputing).toBe(false);
  });

  it("refresh() re-fetches GET endpoint", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ ...FAKE_STABILITY, computed_at: "old" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ ...FAKE_STABILITY, computed_at: "new" }),
      });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useStability("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.refresh();
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result.current.data?.computed_at).toBe("new");
  });

  it("clears data when aeroplaneId becomes null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_STABILITY),
    });

    const { result, rerender } = renderHook(
      ({ id }) => useStability(id),
      { initialProps: { id: "42" as string | null } },
    );

    await waitFor(() => {
      expect(result.current.data).toEqual(FAKE_STABILITY);
    });

    rerender({ id: null });

    expect(result.current.data).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run __tests__/useStability.test.ts`
Expected: FAIL — module `@/hooks/useStability` not found

- [ ] **Step 3: Implement the hook**

Create `frontend/hooks/useStability.ts`:

```typescript
"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface StabilityData {
  id: number;
  aeroplane_id: number;
  solver: string;
  neutral_point_x: number | null;
  mac: number | null;
  cg_x_used: number | null;
  static_margin_pct: number | null;
  stability_class: "stable" | "neutral" | "unstable" | null;
  cg_range_forward: number | null;
  cg_range_aft: number | null;
  Cma: number | null;
  Cnb: number | null;
  Clb: number | null;
  is_statically_stable: boolean;
  is_directionally_stable: boolean;
  is_laterally_stable: boolean;
  trim_alpha_deg: number | null;
  trim_elevator_deg: number | null;
  computed_at: string;
  status: "CURRENT" | "DIRTY";
  geometry_hash: string | null;
}

export interface UseStabilityReturn {
  data: StabilityData | null;
  isLoading: boolean;
  isComputing: boolean;
  error: string | null;
  compute: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useStability(
  aeroplaneId: string | null,
): UseStabilityReturn {
  const [data, setData] = useState<StabilityData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/stability`,
      );
      if (res.status === 404) {
        setData(null);
        return;
      }
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Failed to fetch stability: ${res.status} ${body}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [aeroplaneId]);

  const compute = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsComputing(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/stability_summary/avl`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            velocity: 20,
            alpha: 2,
            beta: 0,
            altitude: 0,
          }),
        },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Compute failed: ${res.status} ${body}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsComputing(false);
    }
  }, [aeroplaneId, refresh]);

  useEffect(() => {
    if (aeroplaneId) {
      refresh();
    } else {
      setData(null);
    }
  }, [aeroplaneId, refresh]);

  return { data, isLoading, isComputing, error, compute, refresh };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run __tests__/useStability.test.ts`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useStability.ts frontend/__tests__/useStability.test.ts
git commit -m "feat(gh-423): add useStability hook with tests"
```

---

### Task 2: MarkerDetailBox Component

**Files:**
- Create: `frontend/components/workbench/MarkerDetailBox.tsx`
- Create: `frontend/__tests__/MarkerDetailBox.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/MarkerDetailBox.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MarkerDetailBox, type MarkerInfo } from "@/components/workbench/MarkerDetailBox";

describe("MarkerDetailBox", () => {
  const npMarker: MarkerInfo = {
    type: "np",
    neutral_point_x: 0.25,
    Cma: -1.2,
    stability_class: "stable",
    solver: "avl",
  };

  const cgMarker: MarkerInfo = {
    type: "cg",
    cg_x_used: 0.20,
    static_margin_pct: 33.3,
    source: "estimate",
  };

  const rangeMarker: MarkerInfo = {
    type: "range",
    cg_range_forward: 0.17,
    cg_range_aft: 0.24,
  };

  it("renders NP details when type is np", () => {
    render(<MarkerDetailBox marker={npMarker} onClose={vi.fn()} />);
    expect(screen.getByText("Neutral Point")).toBeInTheDocument();
    expect(screen.getByText("0.250 m")).toBeInTheDocument();
    expect(screen.getByText("-1.200")).toBeInTheDocument();
    expect(screen.getByText("stable")).toBeInTheDocument();
    expect(screen.getByText("avl")).toBeInTheDocument();
  });

  it("renders CG details when type is cg", () => {
    render(<MarkerDetailBox marker={cgMarker} onClose={vi.fn()} />);
    expect(screen.getByText("Center of Gravity")).toBeInTheDocument();
    expect(screen.getByText("0.200 m")).toBeInTheDocument();
    expect(screen.getByText("33.3%")).toBeInTheDocument();
  });

  it("renders range details when type is range", () => {
    render(<MarkerDetailBox marker={rangeMarker} onClose={vi.fn()} />);
    expect(screen.getByText("CG Range")).toBeInTheDocument();
    expect(screen.getByText("0.170 m")).toBeInTheDocument();
    expect(screen.getByText("0.240 m")).toBeInTheDocument();
    expect(screen.getByText("0.070 m")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<MarkerDetailBox marker={npMarker} onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run __tests__/MarkerDetailBox.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the component**

Create `frontend/components/workbench/MarkerDetailBox.tsx`:

```tsx
"use client";

import { X } from "lucide-react";

interface NpMarker {
  type: "np";
  neutral_point_x: number;
  Cma: number | null;
  stability_class: string | null;
  solver: string;
}

interface CgMarker {
  type: "cg";
  cg_x_used: number;
  static_margin_pct: number | null;
  source: string;
}

interface RangeMarker {
  type: "range";
  cg_range_forward: number;
  cg_range_aft: number;
}

export type MarkerInfo = NpMarker | CgMarker | RangeMarker;

interface Props {
  readonly marker: MarkerInfo;
  readonly onClose: () => void;
}

function Row({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
        {value}
      </span>
    </div>
  );
}

export function MarkerDetailBox({ marker, onClose }: Props) {
  const title =
    marker.type === "np"
      ? "Neutral Point"
      : marker.type === "cg"
        ? "Center of Gravity"
        : "CG Range";

  return (
    <div className="flex min-w-[180px] flex-col gap-2 rounded-xl border border-border bg-card p-3 shadow-lg">
      <div className="flex items-center justify-between">
        <span className="font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-foreground">
          {title}
        </span>
        <button
          onClick={onClose}
          aria-label="close"
          className="flex size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
        >
          <X size={12} />
        </button>
      </div>
      <div className="flex flex-col gap-1">
        {marker.type === "np" && (
          <>
            <Row label="Position" value={`${marker.neutral_point_x.toFixed(3)} m`} />
            <Row label="Cm_alpha" value={marker.Cma != null ? marker.Cma.toFixed(3) : "—"} />
            <Row label="Stability" value={marker.stability_class ?? "—"} />
            <Row label="Solver" value={marker.solver} />
          </>
        )}
        {marker.type === "cg" && (
          <>
            <Row label="Position" value={`${marker.cg_x_used.toFixed(3)} m`} />
            <Row label="Static margin" value={marker.static_margin_pct != null ? `${marker.static_margin_pct.toFixed(1)}%` : "—"} />
            <Row label="Source" value={marker.source} />
          </>
        )}
        {marker.type === "range" && (
          <>
            <Row label="Forward limit" value={`${marker.cg_range_forward.toFixed(3)} m`} />
            <Row label="Aft limit" value={`${marker.cg_range_aft.toFixed(3)} m`} />
            <Row label="Range width" value={`${(marker.cg_range_aft - marker.cg_range_forward).toFixed(3)} m`} />
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run __tests__/MarkerDetailBox.test.tsx`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/MarkerDetailBox.tsx frontend/__tests__/MarkerDetailBox.test.tsx
git commit -m "feat(gh-423): add MarkerDetailBox component with tests"
```

---

### Task 3: StabilitySideView Component

**Files:**
- Create: `frontend/components/workbench/StabilitySideView.tsx`
- Create: `frontend/__tests__/StabilitySideView.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/StabilitySideView.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { StabilityData } from "@/hooks/useStability";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon };
});

import React from "react";
import { StabilitySideView } from "@/components/workbench/StabilitySideView";

const FAKE_DATA: StabilityData = {
  id: 1,
  aeroplane_id: 42,
  solver: "avl",
  neutral_point_x: 0.25,
  mac: 0.15,
  cg_x_used: 0.20,
  static_margin_pct: 33.3,
  stability_class: "stable",
  cg_range_forward: 0.17,
  cg_range_aft: 0.24,
  Cma: -1.2,
  Cnb: 0.05,
  Clb: -0.03,
  is_statically_stable: true,
  is_directionally_stable: true,
  is_laterally_stable: true,
  trim_alpha_deg: 2.5,
  trim_elevator_deg: -3.0,
  computed_at: "2026-05-08T12:00:00Z",
  status: "CURRENT",
  geometry_hash: "abc123",
};

describe("StabilitySideView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Plotly container div", () => {
    const { container } = render(<StabilitySideView data={FAKE_DATA} />);
    const plotDiv = container.querySelector("[data-testid='stability-plot']");
    expect(plotDiv).toBeInTheDocument();
  });

  it("renders KPI badges for static margin and stability class", () => {
    render(<StabilitySideView data={FAKE_DATA} />);
    expect(screen.getByText(/33\.3%/)).toBeInTheDocument();
    expect(screen.getByText(/stable/i)).toBeInTheDocument();
  });

  it("shows DIRTY badge when status is DIRTY", () => {
    const dirtyData = { ...FAKE_DATA, status: "DIRTY" as const };
    render(<StabilitySideView data={dirtyData} />);
    expect(screen.getByText(/outdated/i)).toBeInTheDocument();
  });

  it("renders derivative badges for Cma, Cnb, Clb", () => {
    render(<StabilitySideView data={FAKE_DATA} />);
    expect(screen.getByText(/Cm.α/)).toBeInTheDocument();
    expect(screen.getByText(/Cn.β/)).toBeInTheDocument();
    expect(screen.getByText(/Cl.β/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run __tests__/StabilitySideView.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the component**

Create `frontend/components/workbench/StabilitySideView.tsx`:

```tsx
"use client";

import { useRef, useEffect, useState } from "react";
import type { StabilityData } from "@/hooks/useStability";
import { MarkerDetailBox, type MarkerInfo } from "./MarkerDetailBox";

interface Props {
  readonly data: StabilityData;
}

function Badge({
  label,
  value,
  color,
}: Readonly<{ label: string; value: string; color: string }>) {
  return (
    <div
      className="flex items-center gap-1.5 rounded-full px-2.5 py-1"
      style={{ backgroundColor: `${color}15`, border: `1px solid ${color}30` }}
    >
      <span className="text-[10px] text-muted-foreground">{label}</span>
      <span
        className="font-[family-name:var(--font-jetbrains-mono)] text-[11px]"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  );
}

const STABILITY_COLORS: Record<string, string> = {
  stable: "#30A46C",
  neutral: "#F5A623",
  unstable: "#E5484D",
};

export function StabilitySideView({ data }: Props) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [selectedMarker, setSelectedMarker] = useState<MarkerInfo | null>(null);

  const stabilityColor = STABILITY_COLORS[data.stability_class ?? "neutral"] ?? "#888";

  useEffect(() => {
    const node = plotRef.current;
    if (!node) return;

    let cancelled = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (cancelled) return;

      const np = data.neutral_point_x;
      const cg = data.cg_x_used;
      const mac = data.mac;
      const fwd = data.cg_range_forward;
      const aft = data.cg_range_aft;

      if (np == null || cg == null || mac == null) return;

      const xMin = Math.min(np - mac * 1.2, fwd ?? np - mac, cg) - 0.02;
      const xMax = Math.max(np + mac * 0.3, aft ?? np, cg) + 0.02;

      const traces: Plotly.Data[] = [];
      const shapes: Partial<Plotly.Shape>[] = [];

      // MAC bar
      const macLeX = np - mac;
      shapes.push({
        type: "rect",
        x0: macLeX,
        x1: np,
        y0: -0.15,
        y1: 0.15,
        fillcolor: "rgba(136,136,136,0.12)",
        line: { color: "rgba(136,136,136,0.3)", width: 1 },
      });

      // CG range band
      if (fwd != null && aft != null) {
        const rangeColor = STABILITY_COLORS[data.stability_class ?? "neutral"] ?? "#888";
        shapes.push({
          type: "rect",
          x0: fwd,
          x1: aft,
          y0: -0.3,
          y1: 0.3,
          fillcolor: `${rangeColor}18`,
          line: { color: `${rangeColor}50`, width: 1, dash: "dot" },
        });
      }

      // NP marker (blue diamond)
      traces.push({
        x: [np],
        y: [0],
        mode: "markers+text",
        marker: { symbol: "diamond", size: 14, color: "#3B82F6" },
        text: ["NP"],
        textposition: "top center",
        textfont: { size: 11, color: "#3B82F6", family: "JetBrains Mono" },
        name: "Neutral Point",
        hovertemplate: `NP: ${np.toFixed(3)} m<extra></extra>`,
        showlegend: false,
      });

      // CG marker (orange circle)
      traces.push({
        x: [cg],
        y: [0],
        mode: "markers+text",
        marker: { symbol: "circle", size: 14, color: "#FF8400" },
        text: ["CG"],
        textposition: "top center",
        textfont: { size: 11, color: "#FF8400", family: "JetBrains Mono" },
        name: "Center of Gravity",
        hovertemplate: `CG: ${cg.toFixed(3)} m<extra></extra>`,
        showlegend: false,
      });

      // Annotations
      const annotations: Partial<Plotly.Annotations>[] = [];

      // Static margin label between CG and NP
      if (data.static_margin_pct != null) {
        annotations.push({
          x: (cg + np) / 2,
          y: -0.45,
          text: `SM: ${data.static_margin_pct.toFixed(1)}% MAC`,
          showarrow: false,
          font: { size: 12, color: stabilityColor, family: "JetBrains Mono" },
        });
      }

      // MAC label
      annotations.push({
        x: macLeX + mac / 2,
        y: 0.25,
        text: `MAC: ${(mac * 1000).toFixed(0)} mm`,
        showarrow: false,
        font: { size: 10, color: "#888", family: "JetBrains Mono" },
      });

      const layout: Partial<Plotly.Layout> = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        margin: { t: 30, b: 50, l: 60, r: 30 },
        xaxis: {
          title: { text: "x [m]", font: { size: 11, color: "#888" } },
          range: [xMin, xMax],
          gridcolor: "rgba(136,136,136,0.15)",
          zerolinecolor: "rgba(136,136,136,0.3)",
          tickfont: { size: 10, color: "#888", family: "JetBrains Mono" },
        },
        yaxis: {
          visible: false,
          range: [-0.7, 0.5],
          fixedrange: true,
        },
        shapes,
        annotations,
        dragmode: false,
        hovermode: "closest",
        font: { color: "#ccc" },
      };

      const config: Partial<Plotly.Config> = {
        displayModeBar: false,
        responsive: true,
      };

      await Plotly.newPlot(node, traces, layout, config);

      node.on("plotly_click", (eventData: { points: Array<{ curveNumber: number }> }) => {
        const pt = eventData.points[0];
        if (!pt) return;
        if (pt.curveNumber === 0) {
          setSelectedMarker({
            type: "np",
            neutral_point_x: np,
            Cma: data.Cma,
            stability_class: data.stability_class,
            solver: data.solver,
          });
        } else if (pt.curveNumber === 1) {
          setSelectedMarker({
            type: "cg",
            cg_x_used: cg,
            static_margin_pct: data.static_margin_pct,
            source: "estimate",
          });
        }
      });
    })();

    return () => {
      cancelled = true;
      if (node) {
        import("plotly.js-gl3d-dist-min").then((Plotly) =>
          Plotly.purge(node),
        );
      }
    };
  }, [data, stabilityColor]);

  return (
    <div className="flex flex-1 flex-col gap-3">
      {/* KPI badges */}
      <div className="flex flex-wrap items-center gap-2">
        {data.static_margin_pct != null && (
          <Badge
            label="Static Margin"
            value={`${data.static_margin_pct.toFixed(1)}%`}
            color={stabilityColor}
          />
        )}
        {data.stability_class && (
          <Badge
            label="Class"
            value={data.stability_class}
            color={stabilityColor}
          />
        )}
        {data.Cma != null && (
          <Badge label="Cm.α" value={data.Cma.toFixed(3)} color="#A78BFA" />
        )}
        {data.Cnb != null && (
          <Badge label="Cn.β" value={data.Cnb.toFixed(3)} color="#3B82F6" />
        )}
        {data.Clb != null && (
          <Badge label="Cl.β" value={data.Clb.toFixed(3)} color="#30A46C" />
        )}
        {data.status === "DIRTY" && (
          <Badge label="" value="outdated — geometry changed" color="#F5A623" />
        )}
      </div>

      {/* Plotly chart */}
      <div className="relative flex-1">
        <div ref={plotRef} data-testid="stability-plot" className="h-full w-full" />
        {selectedMarker && (
          <div className="absolute right-4 top-4 z-10">
            <MarkerDetailBox
              marker={selectedMarker}
              onClose={() => setSelectedMarker(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run __tests__/StabilitySideView.test.tsx`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/StabilitySideView.tsx frontend/__tests__/StabilitySideView.test.tsx
git commit -m "feat(gh-423): add StabilitySideView Plotly schematic with tests"
```

---

### Task 4: StabilityPanel Container

**Files:**
- Create: `frontend/components/workbench/StabilityPanel.tsx`
- Create: `frontend/__tests__/StabilityPanel.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/StabilityPanel.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { StabilityData } from "@/hooks/useStability";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon };
});

vi.mock("@/components/workbench/StabilitySideView", () => ({
  StabilitySideView: ({ data }: { data: StabilityData }) =>
    React.createElement("div", { "data-testid": "side-view" }, data.stability_class),
}));

import { StabilityPanel } from "@/components/workbench/StabilityPanel";

const FAKE_DATA: StabilityData = {
  id: 1,
  aeroplane_id: 42,
  solver: "avl",
  neutral_point_x: 0.25,
  mac: 0.15,
  cg_x_used: 0.20,
  static_margin_pct: 33.3,
  stability_class: "stable",
  cg_range_forward: 0.17,
  cg_range_aft: 0.24,
  Cma: -1.2,
  Cnb: 0.05,
  Clb: -0.03,
  is_statically_stable: true,
  is_directionally_stable: true,
  is_laterally_stable: true,
  trim_alpha_deg: 2.5,
  trim_elevator_deg: -3.0,
  computed_at: "2026-05-08T12:00:00Z",
  status: "CURRENT",
  geometry_hash: "abc123",
};

describe("StabilityPanel", () => {
  it("shows empty state when data is null", () => {
    render(
      <StabilityPanel
        data={null}
        isComputing={false}
        error={null}
        onCompute={vi.fn()}
      />,
    );
    expect(screen.getByText(/no stability data/i)).toBeInTheDocument();
  });

  it("shows computing spinner when isComputing and no data", () => {
    render(
      <StabilityPanel
        data={null}
        isComputing={true}
        error={null}
        onCompute={vi.fn()}
      />,
    );
    expect(screen.getByText(/computing/i)).toBeInTheDocument();
  });

  it("shows error banner when error is set", () => {
    render(
      <StabilityPanel
        data={null}
        isComputing={false}
        error="Server error"
        onCompute={vi.fn()}
      />,
    );
    expect(screen.getByText("Server error")).toBeInTheDocument();
  });

  it("renders StabilitySideView when data is present", () => {
    render(
      <StabilityPanel
        data={FAKE_DATA}
        isComputing={false}
        error={null}
        onCompute={vi.fn()}
      />,
    );
    expect(screen.getByTestId("side-view")).toBeInTheDocument();
  });

  it("calls onCompute when Compute Stability button is clicked", async () => {
    const onCompute = vi.fn();
    const user = userEvent.setup();
    render(
      <StabilityPanel
        data={null}
        isComputing={false}
        error={null}
        onCompute={onCompute}
      />,
    );
    await user.click(screen.getByRole("button", { name: /compute stability/i }));
    expect(onCompute).toHaveBeenCalledOnce();
  });

  it("disables compute button when isComputing", () => {
    render(
      <StabilityPanel
        data={FAKE_DATA}
        isComputing={true}
        error={null}
        onCompute={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /computing/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run __tests__/StabilityPanel.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the component**

Create `frontend/components/workbench/StabilityPanel.tsx`:

```tsx
"use client";

import type { StabilityData } from "@/hooks/useStability";
import { StabilitySideView } from "@/components/workbench/StabilitySideView";

interface Props {
  readonly data: StabilityData | null;
  readonly isComputing: boolean;
  readonly error: string | null;
  readonly onCompute: () => void;
}

export function StabilityPanel({ data, isComputing, error, onCompute }: Props) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <div className="flex-1" />
        <button
          onClick={onCompute}
          disabled={isComputing}
          className="flex items-center gap-1.5 rounded-full bg-[#FF8400] px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isComputing ? "Computing..." : "Compute Stability"}
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
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
            No stability data. Click Compute Stability to analyze.
          </span>
        </div>
      )}

      {/* Computing spinner */}
      {isComputing && !data && (
        <div className="flex flex-1 items-center justify-center">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Computing stability analysis...
          </span>
        </div>
      )}

      {/* Content */}
      {data && <StabilitySideView data={data} />}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run __tests__/StabilityPanel.test.tsx`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/StabilityPanel.tsx frontend/__tests__/StabilityPanel.test.tsx
git commit -m "feat(gh-423): add StabilityPanel container with tests"
```

---

### Task 5: Tab Integration

**Files:**
- Modify: `frontend/components/workbench/AnalysisViewerPanel.tsx`
- Modify: `frontend/app/workbench/analysis/page.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/StabilityTab.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { TABS } from "@/components/workbench/AnalysisViewerPanel";

describe("AnalysisViewerPanel TABS", () => {
  it("includes Stability in the tabs list", () => {
    expect(TABS).toContain("Stability");
  });

  it("has Stability as the last tab", () => {
    expect(TABS[TABS.length - 1]).toBe("Stability");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/StabilityTab.test.tsx`
Expected: FAIL — "Stability" not in TABS

- [ ] **Step 3: Add Stability tab to AnalysisViewerPanel**

In `frontend/components/workbench/AnalysisViewerPanel.tsx`:

1. Add import at top:
```typescript
import type { StabilityData } from "@/hooks/useStability";
import { StabilityPanel } from "@/components/workbench/StabilityPanel";
```

2. Update TABS array (line 10):
```typescript
const TABS = ["Assumptions", "Polar", "Trefftz Plane", "Streamlines", "Envelope", "Stability"] as const;
```

3. Add stability props to the Props interface:
```typescript
readonly stability?: StabilityData | null;
readonly isComputingStability?: boolean;
readonly stabilityError?: string | null;
readonly onComputeStability?: () => void;
```

4. Add stability tab rendering after the Envelope tab block (after line 750):
```tsx
{activeTab === "Stability" && (
  <StabilityPanel
    data={stability ?? null}
    isComputing={isComputingStability ?? false}
    error={stabilityError ?? null}
    onCompute={onComputeStability ?? (() => {})}
  />
)}
```

- [ ] **Step 4: Wire useStability in the analysis page**

In `frontend/app/workbench/analysis/page.tsx`:

1. Add import:
```typescript
import { useStability } from "@/hooks/useStability";
```

2. Add hook call (after `envelope` hook, ~line 23):
```typescript
const stability = useStability(aeroplaneId);
```

3. Add "Stability" to `modalTitleByTab` (line ~38):
```typescript
"Stability": "Stability Analysis",
```

4. Pass stability props to `AnalysisViewerPanel` (after `onComputeEnvelope`):
```typescript
stability={stability.data}
isComputingStability={stability.isComputing}
stabilityError={stability.error}
onComputeStability={stability.compute}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/StabilityTab.test.tsx`
Expected: PASS

- [ ] **Step 6: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass, no regressions

- [ ] **Step 7: Commit**

```bash
git add frontend/components/workbench/AnalysisViewerPanel.tsx frontend/app/workbench/analysis/page.tsx frontend/__tests__/StabilityTab.test.tsx
git commit -m "feat(gh-423): integrate Stability tab into Analysis page"
```
