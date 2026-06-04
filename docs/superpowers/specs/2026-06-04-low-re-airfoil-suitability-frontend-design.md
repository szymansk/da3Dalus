# Low-Re Airfoil Suitability — Frontend Surfacing (Design Spec)

- **Date:** 2026-06-04
- **Type:** Feature (enhancement)
- **Status:** Draft for GH Issue
- **Depends on:** #821 (backend: low-Re airfoil suitability scoring + search endpoint)
- **Brainstormed with:** Visual Companion (mockups in `.superpowers/brainstorm/`, gitignored)

## 1. Problem & Motivation

#821 adds a backend that scores every airfoil for low-Re suitability and exposes
`GET /airfoils/db/suitability`. This ticket **surfaces that guidance in the
workbench** so a user picking an airfoil for a wing cross-section sees, at a
glance, whether it fits the model's chord/speed, mission, and operating CL.

The natural home is the **existing** `/workbench/airfoil-preview` screen
(`frontend/app/workbench/airfoil-preview/page.tsx`), which already has:
- a split layout: left `AirfoilPreviewViewerPanel` (NeuralFoil polars for
  root/tip), right 480px `AirfoilPreviewConfigPanel`;
- root + tip `AirfoilSelector`s, a velocity input, and a frontend
  `computeRe(velocity, chordMm)` (ν = 1.46e-5) that already derives `rootRe` /
  `tipRe` and auto-runs `useAirfoilAnalysis` per airfoil;
- editable Re fields per airfoil (orange `#FF8400` root, cyan `#22D3EE` tip).

So `rootRe`/`tipRe`, the chord, the mission/assumptions context, and the polar
charts are **already present** — this feature mostly composes existing pieces.

## 2. Scope

### In scope (frontend only)
- **Hybrid integration** on `/workbench/airfoil-preview`:
  1. `AirfoilSelector` dropdown rows show a **compact suitability badge** and the
     list is **sorted by suitability**;
  2. an inline **Suitability card** under each airfoil's selector + Re field
     showing the **three lenses**;
  3. a **"🔍 Passende finden"** action that turns the dropdown into a **ranked
     list** (by chord→Re + mission + target-CL);
  4. an **operating-point marker** on the existing L/D-vs-α polar (left);
  5. a **tip-Re < root-Re warning banner** in the viewer panel.
- New SWR hook `useAirfoilSuitability` hitting `GET /airfoils/db/suitability`.
- Unit (vitest) + E2E (playwright-bdd) coverage.

### Non-goals
- Backend scoring/endpoint (#821).
- Surfacing suitability outside `/workbench/airfoil-preview` (e.g. in the
  `AeroplaneTree` xsec nodes) — possible later, not here.
- Editing/curating the airfoil library.

## 3. The Three Lenses (display)

Aligned with the existing `score_0_1` language from `useMissionKpis`. Each lens
is a labeled horizontal score bar (green/amber/red by value):
1. **Re-agnostisch** — general low-Re quality at the airfoil's computed Re.
2. **Mission · `<type>`** — mission-weighted (from the model's mission preset).
3. **Ziel-CL · Cruise** and **Ziel-CL · Loiter** — at the operating CLs from the
   model's design assumptions (two bars).

Plus a **confidence chip** (`● Confidence 0.97`, amber when `< 0.85`) and a
**caveat callout** (relative ranking; no hysteresis/roughness modelling;
recommend XFoil/wind-tunnel validation when confidence is low).

## 4. Components & Behaviour

### 4.1 `AirfoilSuitabilityCard` (new, `components/workbench/`)
- Renders the three-lens bars + confidence chip + caveat for one airfoil at one
  Re. Reuses the `Chip` primitive (tooltip/value/color) and the
  `PolarRejectionBadge` amber-callout pattern.
- **Collapsible.** **Root: open by default; Tip: collapsed by default**
  (ChevronDown/ChevronRight toggle, the project's existing collapsible pattern).
- Placed in `AirfoilPreviewConfigPanel` directly under each airfoil's
  `AirfoilSelector` + `ReynoldsField`.

### 4.2 `AirfoilSelector` enhancement
- Per-row **suitability badge** via the existing right-aligned `stats` slot (or a
  small new badge slot); rows **sorted by suitability score** descending.
- **"🔍 Passende finden"** toggle: switches the dropdown into a **ranked list**
  mode — same rows, ordered by the active lens (default: mission when a model is
  loaded, else Re-agnostic), badge becomes the driving score. No separate route.
- **Import-pattern caution:** per project memory, do **not** change the
  `AirfoilSelector` import pattern without real browser testing.

### 4.3 Viewer panel (`AirfoilPreviewViewerPanel`)
- **Operating-point marker** on the existing L/D-vs-α polar at the airfoil's
  operating CL/α (Plotly marker trace; metres-direct, inline figure metadata per
  the project's Plotly conventions). The polar is **not** duplicated in the card.
- **Tip-Re < root-Re warning banner** (red, `AlertTriangle`, `role="alert"`)
  shown when the segment is tapered (`tipRe < rootRe`).

### 4.4 `useAirfoilSuitability` (new hook, `frontend/hooks/`)
- Mirrors `useDesignAssumptions` (SWR + `fetcher` from `lib/fetcher.ts`).
- Calls `GET /airfoils/db/suitability?chord_m=&speed_ms=[&aeroplane_id=]
  [&mission_type=][&target_cl_cruise=][&target_cl_loiter=]`.
- `chord_m`/`speed_ms` from the page state (chord in metres; velocity already in
  state). `aeroplane_id` from `useAeroplaneContext` → enables mission +
  target-CL lenses; without it, only the Re-agnostic lens renders.
- Returns ranked airfoils with the three lenses, `min_analysis_confidence`,
  `family`, caveat, and the tip-Re flag.

## 5. Data Flow

```
airfoil-preview/page.tsx
  ├─ chord (m), velocity → computeRe → rootRe / tipRe   (existing)
  ├─ useAeroplaneContext → aeroplaneId                  (existing)
  ├─ useAirfoilSuitability(chord_m, speed_ms, aeroplaneId)  (NEW)
  │     → ranked list + per-airfoil three-lens scores + confidence + caveat
  ├─ AirfoilPreviewConfigPanel
  │     ├─ AirfoilSelector (badges + sort + "find suitable" ranked mode)  (NEW)
  │     └─ AirfoilSuitabilityCard (root open / tip collapsed)             (NEW)
  └─ AirfoilPreviewViewerPanel
        ├─ L/D polar + operating-point marker                            (NEW)
        └─ tip-Re < root-Re warning banner                               (NEW)
```

## 6. Styling

Dark theme, accent `#FF8400`, JetBrains Mono + Geist. Score bars: green
`#34D399` / amber `#FBBF24` / red `#F87171`. Reuse `Chip`,
`PolarRejectionBadge`, collapsible section, and Plotly dark-layout conventions.
Keep root accent orange `#FF8400`, tip cyan `#22D3EE` consistent with the
existing Re fields.

## 7. Testing Strategy

- **Unit (vitest, `frontend/__tests__/`):**
  - `AirfoilSuitabilityCard` renders three lenses, confidence chip, caveat;
    amber confidence chip when `< 0.85`; collapse/expand toggle.
  - `AirfoilSelector` shows badges, sorts by score, and switches to ranked mode.
  - `useAirfoilSuitability` builds the correct query string (with/without
    `aeroplane_id`).
  - Run with **Node 22** (`nvm use 22`) — Node ≥24 breaks jsdom localStorage.
- **E2E (playwright-bdd, `frontend/e2e/features/`):** stub
  `GET /airfoils/db/suitability` via `page.route()`; scenarios:
  - suitability card with three lenses appears for the selected root airfoil;
  - low-confidence airfoil shows the amber caveat;
  - tapered segment shows the tip-Re warning banner (`role="alert"`);
  - "Passende finden" re-orders the dropdown by score.
- `npm run deps:check` stays green.

## 8. Acceptance Criteria

- [ ] On `/workbench/airfoil-preview`, each `AirfoilSelector` dropdown shows a
      per-airfoil suitability badge and is sorted by suitability.
- [ ] An `AirfoilSuitabilityCard` renders under root (open) and tip (collapsed),
      showing Re-agnostic / Mission / Ziel-CL (Cruise + Loiter) bars + confidence
      chip + caveat, at each airfoil's computed Re.
- [ ] "🔍 Passende finden" re-ranks the dropdown by chord→Re + mission +
      target-CL.
- [ ] The L/D polar shows an operating-point marker; a tip-Re < root-Re warning
      banner (`role="alert"`) appears for tapered segments.
- [ ] `useAirfoilSuitability` correctly degrades to the Re-agnostic lens when no
      `aeroplane_id` is available.
- [ ] Unit + E2E tests cover the above; `deps:check` passes; no `AirfoilSelector`
      import-pattern change without browser verification.

## 9. Open Items for Implementation

- Confirm the exact `useAirfoilSuitability` response shape against the #821
  endpoint once it lands (field names for the three lenses, confidence, family,
  tip-Re flag).
- Decide the default active lens for "Passende finden" (mission when a model is
  loaded, else Re-agnostic) — confirm with a quick browser check.
- Verify operating CL/α source for the polar marker matches the target-CL used by
  the backend lens (consistency between front and #821).
