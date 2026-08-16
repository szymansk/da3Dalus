# frontend-workbench / analysis-dashboards-plotly — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `plotly.js-gl3d-dist-min` installed (the `gl3d` build — streamlines need
      3D).
- [ ] The backend analysis, matching-chart, flight-envelope, airfoil and
      `assumption_computation_context` endpoints.
- [ ] The Tailwind dark tokens in `app/globals.css`.
- [ ] Playwright — jsdom cannot verify that a figure draws.

## Tasks

- [ ] **T-01 — The chart effect pattern.**
  A container ref; an effect that dynamically imports Plotly, guards an
  unmount race with a `cancelled` flag, calls `newPlot`, and purges the node in
  the cleanup.
  - Legacy origin: `frontend/components/workbench/StreamlinesViewer.tsx` (the
    canonical example; the rule comment is at line 7)
  - Definition of done: **no top-level Plotly import anywhere**. Carry the
    comment verbatim — it is 1.5 MB, and the rule is enforced by nothing else.
  - Confidence: 🟢

- [ ] **T-02 — The dark layout object.**
  `paper_bgcolor` / `plot_bgcolor` = `#111111`, `font.color` = `#B8B9B6`,
  grid `#2E2E2E`, plus the figure title carrying the compute inputs.
  - Legacy origin: the eight charting components
  - Definition of done: every figure is legible on the dark background. Record
    that the values are duplicated as literals per figure rather than read from
    the Tailwind theme.
  - Confidence: 🟢

- [ ] **T-03 — `AnalysisViewerPanel`.**
  Five dynamic-import call sites: polar, sweep, distribution, comparison and
  trim figures.
  - Legacy origin: `frontend/components/workbench/AnalysisViewerPanel.tsx`
    (1 567 l.)
  - Definition of done: each figure re-plots when its data changes and purges on
    unmount. **Record the file size as a maintainability gap** — this is the
    largest file in the client.
  - Confidence: 🟢

- [ ] **T-04 — `StreamlinesViewer`.**
  3D streamlines using the `gl3d` build.
  - Legacy origin: `frontend/components/workbench/StreamlinesViewer.tsx`
  - Definition of done: the 3D scene renders in a real browser and is purged on
    unmount (a leaked WebGL context is a hard limit).
  - Confidence: 🟢

- [ ] **T-05 — `VnDiagram` and the flight-envelope figures.**
  - Legacy origin: `frontend/components/workbench/VnDiagram.tsx`
  - Definition of done: envelope limits come from the backend; the client draws
    them without deriving any.
  - Confidence: 🟢

- [ ] **T-06 — `MatchingChartTab`.**
  Constraint lines and the design point from the matching-chart endpoint.
  - Legacy origin: `frontend/components/workbench/MatchingChartTab.tsx`
    (1 518 l.)
  - Definition of done: every constraint line comes from the backend payload —
    no client-side sizing arithmetic (ADR 0004). Record the file size.
  - Confidence: 🟢

- [ ] **T-07 — `WingOutlineViewer`.**
  Plot the planform from backend geometry **in metres**, with no mm conversion.
  - Legacy origin: `frontend/components/workbench/WingOutlineViewer.tsx`
    (1 005 l.)
  - Definition of done: a test asserts no `* 1000` / `/ 1000` appears on the
    outline path. This contradicts the general "mm in WingConfig" intuition and
    is a documented exception — annotate it in the file.
  - Confidence: 🟢

- [ ] **T-08 — Airfoil preview charts.**
  `AirfoilProxyChart` and `AirfoilPreviewViewerPanel`, plus the suitability
  card.
  - Legacy origin: `frontend/components/workbench/AirfoilProxyChart.tsx`,
    `AirfoilPreviewViewerPanel.tsx` (1 039 l.)
  - Definition of done: suitability values come from
    `/airfoils/db/suitability`; the client only formats them.
  - Confidence: 🟢

- [ ] **T-09 — The metrics band (gh-881).**
  A compact docked band of semantic widgets including `PlanformDiagram`; one
  column expandable to full width **at constant band height**; numbers inline or
  on hover.
  - Legacy origin: `frontend/components/workbench/metrics-dashboard/` (7 files)
  - Definition of done: the band stays compact by default and does not become a
    stack of full-width rows when expanded. Numbers read from
    `assumption_computation_context`, mass/CG and stability — never derived.
  - Confidence: 🟡

- [ ] **T-10 — Compute inputs inside the figure.**
  Velocity, altitude, α range and solver in each figure's title or annotations.
  - Legacy origin: the project convention
  - Definition of done: an exported PNG states what it was computed with,
    without the surrounding panel.
  - Confidence: 🟡

### Remediation (behaviour changes — each needs a decision)

- [ ] **T-11 — Remove `react-plotly.js`.**
  - Legacy origin: `frontend/package.json:37`
  - Definition of done: the dependency is gone and nothing breaks — it is never
    imported.
  - Confidence: 🟡 (a decision, trivially safe)

- [ ] **T-12 — Extract a shared dark layout template.**
  One module exporting the base layout, ideally reading the Tailwind token
  values rather than duplicating literals.
  - Legacy origin: eight duplicated layout objects
  - Definition of done: a token change updates every figure.
  - Confidence: 🟡 (a decision)

- [ ] **T-13 — Guard the bundle rule automatically.**
  A lint rule or a CI bundle-size check that fails on a top-level Plotly import.
  - Legacy origin: `StreamlinesViewer:7` (a comment is the only enforcement)
  - Definition of done: adding a top-level import fails CI.
  - Confidence: 🟡 (a decision)

- [ ] **T-14 — Move `metricsMock.ts` out of the production tree.**
  - Legacy origin: `components/workbench/metrics-dashboard/metricsMock.ts`
  - Definition of done: mock data lives with the tests.
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — Static rule:** scan every module; none imports `plotly.js` or
      `react-plotly.js` at top level.
- [ ] **TT-02 — Runtime import:** the import happens inside the effect.
- [ ] **TT-03 — Purge:** `Plotly.purge` is called with the container node on
      unmount.
- [ ] **TT-04 — Re-plot:** changing the data re-plots the figure.
- [ ] **TT-05 — Unmount race:** unmounting during the import does not plot into
      a detached node.
- [ ] **TT-06 — Dark palette:** the layout carries the dark background and
      muted font colour.
- [ ] **TT-07 — No client arithmetic:** a grep-style test asserts the drag split,
      neutral point and static margin are read, not computed.
- [ ] **TT-08 — Outline units:** no mm conversion on the outline path.
- [ ] **TT-09 — Figure self-description:** the title contains the compute
      inputs.
- [ ] **TT-10 — Metrics band (Playwright):** compact by default; expanding one
      column keeps the band height.
- [ ] **TT-11 — Rendering (Playwright):** each figure type actually draws.

> TT-10 and TT-11 **must** run in a real browser — className-only jsdom tests
> cannot verify scroll, overflow or layout, and Plotly does not draw in jsdom.

## Suggested Order

1. **T-01 → T-02** the effect pattern and the layout object once, correctly.
   Every other task repeats them. Add TT-01 immediately — the bundle rule is
   otherwise enforced only by a comment.
2. **T-04** streamlines first among the figures: it is the reason the `gl3d`
   build is used and the harshest test of purge/disposal.
3. **T-03** the analysis panel's five figures.
4. **T-05 → T-08** envelope, matching chart, outline and airfoil charts. T-07
   (outline in metres) needs its unit test written first — the mm assumption is
   the natural mistake.
5. **T-09 → T-10** the metrics band and figure self-description, verified in a
   browser.
6. **T-11 → T-14** the remediations. T-11 (drop the unused dependency) and T-13
   (automate the bundle rule) are cheap and high-value; T-12 (shared template)
   touches all eight components.

## Pending Gaps

- **Should `react-plotly.js` be removed?** It is declared and never imported —
  and it is the package whose use would break the bundle rule.
- **Should the dark layout be a shared template** reading Tailwind tokens
  instead of eight duplicated literal sets?
- **Should the bundle rule be enforced automatically** (lint rule or CI
  bundle-size check) rather than by a comment?
- **Should `metricsMock.ts` move out of the production tree?**
- **Should `AnalysisViewerPanel` (1 567 l.) and `MatchingChartTab` (1 518 l.) be
  decomposed?**
- **Should large polars and streamline fields be downsampled** before plotting?
- **Should figure render time and payload size be measured?**
- **Should the other solver-adjacent routers get `NonFiniteSafeJSONResponse`**,
  so a NaN cannot 500 before the chart is reached? (That decision belongs to
  `platform-core`.)
