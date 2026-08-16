# frontend-workbench / analysis-dashboards-plotly

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

Every chart in the workbench — polars, streamlines, V-n diagrams, matching
charts, airfoil proxies, planform outlines and the docked metrics band — is a
**runtime-imported Plotly figure**, themed per figure for the dark palette and
purged on unmount. 🟢

The single non-negotiable rule is stated in code: *"DO NOT import
react-plotly.js or plotly.js at top level — it is 1.5 MB."*
(`StreamlinesViewer:7`). 🟢

## Responsibilities

- Render every analysis figure through a runtime-imported Plotly. 🟢
- Apply the dark palette to each figure. 🟢
- Purge each figure on unmount. 🟢
- Render the docked metrics band (gh-881). 🟢
- Render the planform/outline views. 🟢

## Business Rules

- **BR-FE18 — Plotly is always a runtime import.** 🟢
  `await import("plotly.js-gl3d-dist-min")` inside an effect, with
  `Plotly.purge(node)` on unmount. Eight components chart;
  `AnalysisViewerPanel` performs the dynamic import at **five** separate call
  sites.
- **BR-FE35 — 🟢 **`react-plotly.js` is removed from `package.json`** (`R2-13`, `P-DEAD-0`): declared, never imported; the charts use `plotly.js-gl3d-dist-min` directly. Previously:
  `package.json:37` — dead weight in the dependency tree.
- **BR-FE19 — Dark theming is per figure.** 🟢 `paper_bgcolor`, `plot_bgcolor`
  and `font.color` set on each figure rather than through a shared layout
  template. 🟡 Duplicated across eight components.
- **BR-FE36 — The frontend never computes a displayed number.** 🟢 Every value
  comes from the backend — the polar, the drag split, the neutral point, the
  static margin (gh-924 / ADR 0004). The client formats and plots; it does not
  derive.
- **BR-FE37 — `WingOutlineViewer` consumes metres directly.** 🟢 It plots
  backend geometry in metres with **no mm conversion**, despite the general
  "mm in WingConfig" rule — the outline data arrives already in metres.
- **BR-FE38 — Compute-input parameters belong inside the figure.** 🟡 The
  project convention is that the parameters a chart was computed with (velocity,
  altitude, α range) appear in the figure's own title or annotations, not in the
  surrounding chrome, so a saved or exported image stays self-describing.
- **BR-FE39 — The metrics band is a compact dashboard, not a chip strip.** 🟡
  gh-881: semantic visual widgets in a compact band, one expandable to full
  width at constant height; numbers are always available inline or on hover.
- **BR-FE40 — 🟢 `metricsMock.ts` is dead code and is deleted (`Q-FW-8`, resolved by code lookup: zero imports from production, tests or e2e — all four `metricsMock` hits are comments). Previously mock data
  inside `components/workbench/metrics-dashboard/`.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Import Plotly at runtime inside an effect | Must | No top-level `plotly.js` or `react-plotly.js` import anywhere |
| RF-02 | Purge each figure on unmount | Must | `Plotly.purge(node)` in the cleanup |
| RF-03 | Apply the dark palette per figure | Must | `paper_bgcolor`, `plot_bgcolor`, `font.color` |
| RF-04 | Re-plot when the underlying data changes | Must | The effect's dependency list covers the data |
| RF-05 | Render the analysis panel's five figure types | Must | Polar, sweep, streamlines, V-n, trim interpretation |
| RF-06 | Render the matching chart | Must | `MatchingChartTab` (1 518 l.) 🟡 |
| RF-07 | Render the airfoil proxy chart and suitability card | Must | Airfoil preview tab |
| RF-08 | Render the planform / wing outline in metres | Must | No mm conversion |
| RF-09 | Render the docked metrics band | Must | gh-881, compact, expandable |
| RF-10 | Display only backend-computed numbers | Must | No client-side aerodynamics |
| RF-11 | Put compute inputs inside the figure | Should | Title or annotations |
| RF-12 | Share a dark layout template | Should | 🟡 duplicated per figure today |
| RF-13 | Remove the unused Plotly React wrapper | Should | 🟡 still declared |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Performance | The 1.5 MB Plotly bundle must never enter the initial payload | `StreamlinesViewer:7` + 8 dynamic import sites | 🟢 |
| Memory | Figures must be purged so detached DOM and WebGL contexts are released | `Plotly.purge` on unmount | 🟢 |
| Correctness | No displayed number may be derived in the client | ADR 0004; the copilot's deterministic-numbers rule applies system-wide | 🟢 |
| Consistency | Every figure must read as part of one dark system | per-figure theming | 🟡 (duplicated) |
| Self-description | An exported figure must state what it was computed with | project convention | 🟡 |
| Bundle hygiene | 🟡 An unused 1.5 MB-class dependency is declared | `package.json:37` | 🟡 |
| Maintainability | 🟡 `AnalysisViewerPanel` (1 567 l.) and `MatchingChartTab` (1 518 l.) are the two largest files in the client | — | 🟡 |
| Testability | 🟡 Chart rendering is verifiable only in a real browser; jsdom cannot draw | — | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Bundle hygiene

  Scenario: No top-level Plotly import
    When I scan every module under app/, components/, hooks/ and lib/
    Then none imports plotly.js or react-plotly.js at top level

  Scenario: Runtime import
    When a charting component mounts
    Then plotly.js-gl3d-dist-min is imported inside the effect

  Scenario: Cleanup
    When a charting component unmounts
    Then Plotly.purge is called on its container node

Feature: Theming

  Scenario: Dark figures
    Given any figure
    Then paper_bgcolor and plot_bgcolor are the dark background
    And font.color is the muted foreground

  Scenario: Re-plot on data change
    Given a polar figure
    When the underlying analysis result changes
    Then the figure is re-plotted

Feature: Numbers

  Scenario: The client does not compute
    Given a drag breakdown shown in the analysis panel
    Then the induced/parasite split came from the backend
    And no client code computes CL^2 / (pi * AR * e)

  Scenario: One neutral point
    Given the metrics band and the analysis panel both show a neutral point
    Then both read it from assumption_computation_context

  Scenario: Outline units
    Given wing outline data from the backend in metres
    Then WingOutlineViewer plots it directly with no mm conversion

Feature: Figure self-description

  Scenario: Compute inputs inside the figure
    Given a polar computed at a given velocity and altitude
    Then those parameters appear in the figure's title or annotations
    And not only in the surrounding panel chrome

Feature: The metrics band

  Scenario: Compact by default
    Then the band occupies a compact strip of columns
    And numbers are readable inline or on hover

  Scenario: Expansion keeps the height
    When one column is expanded
    Then it fills the width at the same band height
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Runtime-only Plotly import (RF-01) | Must | 1.5 MB in the initial bundle otherwise |
| Purge on unmount (RF-02) | Must | Detached DOM and WebGL contexts leak otherwise |
| Per-figure dark theming (RF-03) | Must | The app is dark-only |
| Re-plot on data change (RF-04) | Must | Stale charts are worse than none |
| The chart inventory (RF-05…RF-09) | Must | The analysis product itself |
| Backend-only numbers (RF-10) | Must | ADR 0004 |
| Compute inputs inside the figure (RF-11) | Should | Keeps an exported image self-describing |
| A shared layout template (RF-12) | Should | 🟡 duplicated across 8 components |
| Removing `react-plotly.js` (RF-13) | Should | 🟡 unused dependency |
| Client-side aerodynamics | Won't | ADR 0004 — every number is computed server-side |
| A light theme for charts | Won't | Dark-only app |
| Server-side chart rendering | Won't | Charts are interactive and client-only |

## Code Traceability

| File | Role | Coverage |
|---|---|---|
| `frontend/components/workbench/StreamlinesViewer.tsx:7` | the "DO NOT import at top level" rule | 🟢 |
| `frontend/components/workbench/AnalysisViewerPanel.tsx` (1 567 l.) | 5 dynamic-import call sites | 🟢 🟡 |
| `frontend/components/workbench/AnalysisConfigPanel.tsx` (1 063 l.) | analysis inputs | 🟢 🟡 |
| `frontend/components/workbench/OperatingPointsPanel.tsx` (1 076 l.) | operating points | 🟢 🟡 |
| `frontend/components/workbench/VnDiagram.tsx` | flight envelope | 🟢 |
| `frontend/components/workbench/MatchingChartTab.tsx` (1 518 l.) | matching chart | 🟢 🟡 |
| `frontend/components/workbench/WingOutlineViewer.tsx` (1 005 l.) | planform in **metres** | 🟢 |
| `frontend/components/workbench/AirfoilProxyChart.tsx`, `AirfoilPreviewViewerPanel.tsx` (1 039 l.) | airfoil preview | 🟢 |
| `frontend/components/workbench/metrics-dashboard/` (7 files, gh-881) incl. `PlanformDiagram` | the docked band | 🟢 |
| `frontend/components/workbench/metrics-dashboard/metricsMock.ts` | mock data in the production tree | 🟡 |
| `frontend/components/workbench/trim-interpretation/` | trim result figures | 🟢 |
| `frontend/package.json:34,37` | `plotly.js-gl3d-dist-min` (used) and `react-plotly.js` (unused) | 🟢 🟡 |
