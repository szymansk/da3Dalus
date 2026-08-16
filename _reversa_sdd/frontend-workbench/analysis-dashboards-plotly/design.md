# frontend-workbench / analysis-dashboards-plotly — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).

## Interface

There is no shared chart abstraction. Each charting component owns its own
effect, its own dynamic import and its own layout object. 🟡

```tsx
// the pattern, repeated in 8 components (5× inside AnalysisViewerPanel alone)
const ref = useRef<HTMLDivElement>(null);

useEffect(() => {
  const node = ref.current;
  if (!node || !data) return;
  let cancelled = false;
  (async () => {
    const Plotly = await import("plotly.js-gl3d-dist-min");   // 1.5 MB — RUNTIME ONLY
    if (cancelled) return;
    await Plotly.newPlot(node, traces, layout, config);
  })();
  return () => {
    cancelled = true;
    import("plotly.js-gl3d-dist-min").then(P => P.purge(node));
  };
}, [data, ...]);
```

The layout object carries the dark palette explicitly:

```ts
const layout = {
  paper_bgcolor: "#111111",       // --color-background
  plot_bgcolor:  "#111111",
  font: { color: "#B8B9B6" },     // --color-muted-foreground
  xaxis: { gridcolor: "#2E2E2E" },// --color-border
  yaxis: { gridcolor: "#2E2E2E" },
  title: `Polar — V = ${v} m/s, h = ${h} m, α ∈ [${a0}, ${a1}]`,   // compute inputs INSIDE
  ...
};
```

## Main Flow

### F1 — The bundle rule 🟢

`StreamlinesViewer:7` states it verbatim: *"DO NOT import react-plotly.js or
plotly.js at top level — it is 1.5 MB."* Consequences:

- every chart import is inside an effect, never at module scope;
- the first tab render never pays for Plotly;
- `react-plotly.js` — the React wrapper that **would** force a top-level import —
  is declared in `package.json` and **never used**. 🔴

### F2 — The figure inventory 🟢

| Component | Figures |
|---|---|
| `AnalysisViewerPanel` (1 567 l.) | 5 dynamic-import call sites — polar, sweep, distribution, comparison, trim |
| `StreamlinesViewer` | 3D streamlines (the `gl3d` bundle's reason for being) |
| `VnDiagram` | flight envelope V-n |
| `MatchingChartTab` (1 518 l.) | the T/W vs W/S matching chart |
| `WingOutlineViewer` (1 005 l.) | planform outline, **metres** |
| `AirfoilProxyChart` / `AirfoilPreviewViewerPanel` (1 039 l.) | airfoil polars and shape |
| `metrics-dashboard/PlanformDiagram` + siblings (gh-881) | the docked band |
| `trim-interpretation/*` | trim result figures |

### F3 — Units 🟢

`WingOutlineViewer` plots backend geometry **in metres with no conversion**,
which contradicts the general "mm in WingConfig" intuition and is therefore
worth stating explicitly: the outline payload arrives in metres, the same units
the database and AeroSandbox use (ADR 0001). The mm world stops at the
`wingconfig` editor. 🟢

### F4 — Numbers 🟢

The client formats and plots; it never derives. Concretely:

| Value | Source |
|---|---|
| polar points, `cl_max`, `cd_min`, L/D | the backend analysis endpoint |
| induced / parasite drag split | the backend (`_drag_breakdown`) — ADR 0004 |
| neutral point, static margin | `assumption_computation_context` (gh-924) |
| mass, CG | the mass & CG endpoints |
| matching-chart constraint lines | the matching-chart endpoint |

There is deliberately **no** aerodynamics in the client, so the app can never
show two different answers for one quantity. 🟢

### F5 — Figure self-description 🟡

The project convention: the parameters a chart was computed with (velocity,
altitude, α range, solver) go **inside** the Plotly figure — its title or
annotations — not into the surrounding panel chrome, so a screenshot or exported
PNG remains self-describing. 🟡

### F6 — The metrics band (gh-881) 🟡

A compact docked band of semantic widgets rather than a chip strip: one row of
columns occupying a small share of the viewport, with a single column expandable
to full width **at constant band height**. Numbers are always available inline or
on hover. `PlanformDiagram` is the visual anchor.
🟡 `metricsMock.ts` ships alongside the production components (`Q-FW-8`, resolved by code lookup).

## Alternative Flows

- **No data yet:** the effect returns early; the container stays empty with a
  loading state. 🟢
- **Data changes:** the effect re-runs and `newPlot` replaces the figure. 🟢
- **Unmount during the dynamic import:** the `cancelled` flag prevents plotting
  into a detached node. 🟡
- **Unmount after plotting:** `Plotly.purge(node)` releases the figure. 🟢
- **A NaN in the payload:** the `aeroanalysis` router renders it as `null`
  (`NonFiniteSafeJSONResponse`), so the chart shows a gap rather than crashing —
  but any **other** solver-adjacent router can still 500 before the client sees
  anything (`platform-core` 🔴).
- **A very large polar:** no downsampling; the figure plots every point. 🟡
- **Several charts on one tab:** each imports Plotly independently; the module
  is cached by the bundler after the first. 🟢

## Dependencies

- `plotly.js-gl3d-dist-min` (runtime import only).
- The backend analysis, matching-chart, envelope, airfoil and
  computation-context endpoints — see [`../contracts.md`](../contracts.md).
- The Tailwind token values, duplicated as literals inside each layout
  object. 🟡

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Runtime-only Plotly import, enforced by a comment rule | `StreamlinesViewer:7` | 🟢 |
| Use the `gl3d` distribution (streamlines need 3D) | `package.json:34` | 🟢 |
| Purge on unmount rather than relying on GC | the effect cleanups | 🟢 |
| Theme each figure explicitly instead of a shared template | 8 components | 🟡 |
| Keep every computed number on the backend | ADR 0004 | 🟢 |
| Plot the wing outline in metres, no conversion | `WingOutlineViewer` | 🟢 |
| Put compute inputs inside the figure | project convention | 🟡 |
| A compact metrics band rather than a chip strip | gh-881 | 🟡 |
| Keep `react-plotly.js` declared but unused | — | 🟡 no rationale |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| the Plotly figure | attached to the container DOM node | until `purge` on unmount |
| the `cancelled` flag | closure per effect | guards the import/unmount race |
| chart data | the SWR cache | revalidated like any other server state |
| metrics-band expansion | component state | transient |

No chart state is persisted; a reload re-fetches and re-plots. 🟢

## Observability

- 🟡 Errors surface per panel through the owning hook's `error` field.
- 🔴 No measurement of figure render time or payload size, despite polars and
  streamline fields being the largest responses in the app.
- 🔴 No detection of a Plotly import that accidentally becomes top-level — the
  rule is enforced only by a comment and review.

## Risks and Gaps

- 🔴 **`react-plotly.js` is a declared, never-imported dependency** — the exact
  package whose use would break the bundle rule.
- 🔴 **Dark theming is duplicated across eight components**, with token values
  hard-coded as literals rather than read from the Tailwind theme.
- 🔴 **`AnalysisViewerPanel` (1 567 l.) and `MatchingChartTab` (1 518 l.)** are
  the two largest files in the client; the tab pages are thin, the panels are
  not.
- 🔴 **`metricsMock.ts` ships in the production component tree.**
- 🔴 **Nothing prevents a future top-level Plotly import** except a comment —
  no lint rule, no bundle-size check in CI.
- 🟡 **No downsampling** for large polars or streamline fields.
- 🟡 **Chart rendering cannot be verified in jsdom**; only Playwright can prove a
  figure actually draws.
- 🟡 **Only `aeroanalysis` is NaN-protected** on the backend, so another
  solver-adjacent endpoint can 500 before the chart is ever reached.
