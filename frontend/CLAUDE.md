@AGENTS.md

## da3Dalus Construction Workbench Frontend

- Backend API: http://localhost:8000 (FastAPI)
- Swagger UI: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
- MCP endpoint: http://localhost:8000/mcp
- This frontend connects to the cad-modelling-service backend
- Use App Router (not Pages Router)
- All API calls go through server-side route handlers or
  server actions to avoid CORS
- Dark theme with orange accent (#FF8400), fonts: JetBrains Mono + Geist

## Design Rules

### Reuse before creating

Before building a new component, **search the existing frontend**
for patterns that match. This project has battle-tested components:

- `TreeCard` + `SimpleTreeRow` — collapsible tree panels with DnD
- `AirfoilSelector` — searchable dropdown (reuse for any picker)
- `Field` — labeled number/text input with suffix
- `GroupAddMenu` — contextual add-action popover
- Collapsible sections (`ChevronDown`/`ChevronRight` toggle)
- Modal dialogs (`fixed inset-0 z-50` backdrop + card)
- SWR hooks (`useWing`, `useComponents`, `useComponentTypes`, etc.)

Check `frontend/components/workbench/` and `frontend/hooks/` first.
Only create new components when no existing pattern fits.

### Click-dummy for large UI changes

For new screens, major layout changes, or complex interactions:
build a **click-dummy** (functional prototype with hardcoded data)
and review it with the user before implementing the real logic.
Small additions (new form fields, extra buttons) that follow
existing patterns don't need a click-dummy.

### Adding Analysis Types

Each analysis type is a tab in the Analysis page
(`frontend/app/workbench/analysis/`) with its own:

1. **Tab entry** in `AnalysisViewerPanel.tsx` TABS array
2. **Config section** in `AnalysisConfigPanel.tsx` (keyed by
   `activeTab` prop)
3. **Hook** in `frontend/hooks/` for the backend endpoint
4. **Plotly charts** for result visualization

Pattern: Tab selection → "Configure & Run" opens tab-specific
modal → user sets parameters → Run → results displayed as Plotly
charts. Future analysis types (e.g. stability/trim with operating
point) follow the same pattern.

All analysis charts use **Plotly** (dynamic import via
`import("plotly.js-gl3d-dist-min")`). Dark theme via layout
props (`paper_bgcolor`, `plot_bgcolor`, `font.color`).
