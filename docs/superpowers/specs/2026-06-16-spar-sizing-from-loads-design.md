# Spar Sizing from Spanwise Loads — Design

**Date:** 2026-06-16
**Status:** Design — awaiting review
**Related:** #1002 (spanwise shear + bending-moment distribution — provides M(y), the input;
spar *sizing* was explicitly out-of-scope there; **this feature depends on #1005/#1002
landing**), #57 (parametric carbon-tube component), #615/#924 (aero context).
**Sources:** user scan `Scannen1503002.jpg` (section-modulus W formulas) +
https://www.flugmodellbau-kirch.de/Hauptholm.htm (erf. W = M/σ method, σ values).

## 1. Goal

In the **Spanwise Loads** analysis tab, derive the required **spar dimensions** from the
computed bending-moment distribution M(y), for a chosen **material** (from the Component DB)
and **spar shape**, using the **limit load factor from the Assumptions** × a user **safety
factor**. The spar's outer dimension at each station is bounded by the **local airfoil
thickness**, so the result is a (tapered) spar dimensioned along the span. **All UI text is
English.**

## 2. Decisions (brainstorming, 2026-06-16)

| Topic | Decision |
|---|---|
| **UI language** | **English** (project convention). Domain terms: Spar, Tube, Rod, Rectangular spar, Capped spar; Pine; packing factor. |
| Load factor | `g_limit` **from the design Assumptions** (read-only in UI; fallback + warning if missing, gh-960 pattern). |
| Safety factor `j` | Editable, default **1.5**. |
| Design moment | `M_design(y) = |M(y)| · g_limit · j`. |
| Outer-dimension constraint | = **local airfoil thickness**: `t_profil(y) = chord(y) · (t/c)(y) · packing`. |
| Packing factor | Editable, default **0.8**. |
| **Materials** | **From the Component DB**, not hardcoded. Extend the existing **`material`** component type additively; seed **Pine** + **Carbon Fiber**. Dropdown lists material components that have an allowable stress. σ_allow auto-fills from the selected material (editable override). |
| Material properties | `density_kg_m3` (already on `material`), **`allowable_bending_stress_mpa`** (new), `youngs_modulus_gpa` (new, optional — for future deflection). |
| Shapes | **Tube**, **Rod** (solid round), **Rectangular spar**, **Capped spar** (upper/lower flange). |
| Compute location | Backend (deterministic, testable); frontend displays. |
| Output | Root headline + spanwise (tapered) solved-dimension table + feasibility flags + **estimated spar mass** (from density). |

## 3. Materials in the Component DB

Extend the existing `material` component_type (currently 3D-print-oriented:
`density_kg_m3`, `print_resolution_mm`, …) **additively** with:
- `allowable_bending_stress_mpa` (number, MPa) — σ_allow used for sizing.
- `youngs_modulus_gpa` (number, GPa, optional) — for a future deflection check.

Both optional → existing 3D-print material rows stay valid. Seed two structural materials:

| Component (type `material`) | density_kg_m3 | allowable_bending_stress_mpa | youngs_modulus_gpa |
|---|---|---|---|
| **Pine** (Kiefer, Güte A) | 500 | 39 (400 kg/cm² compression, kirch — compression governs) | ~11 |
| **Carbon Fiber** | 1600 | 500 (conservative, buckling-aware) | ~120 |

Values are seeded but **editable** in the DB (layup/grade dependent). The spar-sizing
material dropdown = `GET /components?component_type=material` filtered to those with
`allowable_bending_stress_mpa` set. Selecting one fills σ_allow (and density for mass);
the user can override σ_allow inline.

## 4. Section-modulus W formulas

Dimensions in **mm** → W in **mm³** (matches the scan). Internally SI; convert at the boundary.

| Shape | W | Source |
|---|---|---|
| **Rectangular spar** (b×h) | `b·h²/6` | scan A |
| **Capped spar** (b, H outer, h inner gap) | `b·(H³−h³)/(6·H)` | scan B |
| **Rod** (solid round, d) | `d³/10` | scan C |
| **Tube** (Dₐ outer, Dᵢ inner) | `π·(Dₐ⁴−Dᵢ⁴)/(32·Dₐ)` | standard |

## 5. Per-station computation (main wing)

For each station y (uses gh-1002 per-strip M(y) and chord(y), sized on `max(|M_sb|,|M_pt|)`):
1. `M_design = |M(y)| · g_limit · j`
2. `erf_W = M_design / σ_allow`
3. `t_profil = chord(y) · (t/c)(y) · packing`  (outer dim; (t/c) from the section airfoil)
4. Solve the free dimension (outer set to `t_profil`):
   - **Tube:** `Dₐ = t_profil` → `Dᵢ = (Dₐ⁴ − 32·erf_W·Dₐ/π)^¼`, wall `t = (Dₐ−Dᵢ)/2`; infeasible when `32·erf_W·Dₐ/π ≥ Dₐ⁴` → "solid needed".
   - **Rod:** `d = (10·erf_W)^⅓`; feasibility `d ≤ t_profil` else "rod too big".
   - **Rectangular:** `h = t_profil` → `b = 6·erf_W/h²`.
   - **Capped:** `H = t_profil`, `b` (cap width) given → `h = (H³ − 6·H·erf_W/b)^⅓`, gurt thickness `=(H−h)/2`; infeasible when `H³ < 6·H·erf_W/b`.
5. **Spar mass** (estimate): integrate cross-section area × density along the (half) span;
   report per half and full.

## 6. UI (extends the existing Spanwise Loads tab — English)

The V(y)/M(y) Plotly chart stays on top; a collapsible **"Spar Sizing"** panel is added below:

```
▼ Spar Sizing
┌ Inputs ───────────────────────────────────────────────────────────────┐
│ Material [ Carbon Fiber ▾ ] (from Component DB)   Spar shape [ Tube ▾ ] │
│ σ_allow [ 500 ] MPa (from material, editable)                           │
│ Load factor n (limit) [ 4.0 ] from Assumptions  ⚠ default — recompute   │
│ Safety factor j [ 1.5 ]   Packing factor [ 0.80 ]   Cap width b [ — ]   │
└─────────────────────────────────────────────────────────────────────────┘
┌ Result @ root (y=0) ───────────────────────────────────────────────────┐
│ M_design = M·n·j = 24 030 N·m   Required W = 48 060 mm³                  │
│ Outer Ø (= 0.8·t/c·chord) = 118 mm                                       │
│ → Tube  Ø 118 × 2.3 mm wall   ✅ fits profile   Est. mass ≈ 0.42 kg     │
└─────────────────────────────────────────────────────────────────────────┘
┌ Required size along span (tapered) ────────────────────────────────────┐
│ y(m)  chord  profile-t  outer  solved      status                       │
│ 0.00  1.49   118 mm     118    2.3 mm wall  ✅                           │
│ …                                                                       │
│ 5.43  0.30    24 mm      24    solid        ⚠ rod/solid needed          │
└─────────────────────────────────────────────────────────────────────────┘
```
Inputs adapt to the shape (Cap width only for Capped; the "solved" column is wall t / width
b / gurt thickness / d accordingly). Compute inputs echoed inside the figure (project
convention). g_limit shown read-only with a warning when it fell back to a default.

## 7. Architecture

- **Backend pure service** `app/services/spar_sizing.py`: the four `section_modulus_*`
  helpers, `required_section_modulus(m_design, σ)`, `solve_dimension(shape, erf_w, outer,
  cap_width=None)`, `spar_mass(...)`, and `compute_spar_sizing(spanwise_result, chord_by_y,
  tc_by_y, material, params)`. Pure → fast-tier unit-testable, no aero/DB dependency.
- **Schema** `app/schemas/spar_sizing.py`: `SparSizingParams`, `SparSizingStation`,
  `SparSizingResult`.
- **Material type migration**: Alembic + `seed_default_types` update — add the two optional
  fields to the `material` schema; data migration/seed for Pine + Carbon Fiber components.
- **Endpoint:** extend the gh-1002 spanwise-loads response with an optional `spar_sizing`
  block when sizing params (material id, shape, j, packing, σ override, cap width) are
  supplied; `g_limit` from the aeroplane's design assumptions (fallback + warning).
- **Frontend:** the "Spar Sizing" panel; material dropdown from `useComponents`
  (`component_type=material`); selecting a material fills σ_allow + density.

## 8. Data dependency

chord(y) is in the spanwise result. **(t/c)(y)** — section airfoil max thickness ratio —
pulled from the wing sections' airfoils (airfoil DB has thickness). If unavailable for a
section, fall back to t/c = 0.12 **with a warning**, never silently.

## 9. Units

Internally SI. kirch σ (kg/cm²) → MPa ×0.0980665 (Pine 400 → 39.2 MPa). UI: mm / MPa /
kg. W evaluated in mm (→ mm³).

## 10. Testing (>80%)

- Pure `spar_sizing` unit tests per shape (known M,σ,outer → known dim; feasibility flags;
  unit conversions; mass).
- Material-schema migration test (existing material rows stay valid; Pine/CF seed validates).
- Endpoint test — mock the spanwise/strip-forces boundary with the **real** result shape
  (`strip_forces` key — recurring mock-vs-real lesson).
- Frontend panel test (Node 22): material dropdown from DB, σ_allow autofill, shape-adaptive
  inputs, result + flags + g_limit warning.

## 11. Out of scope (follow-ups)

- Explicit **buckling** and **deflection (E·I)** checks (stress-based with buckling-aware
  σ_allow; E is seeded for a later deflection slice).
- Torsion, shear-web, root-joint/Steckung sizing.
- Gust envelope (uses maneuver `g_limit`).
- Non-main-wing surfaces; multi-material composite W (kirch: same-modulus only).
- Auto-matching the solved Tube to a standard/COTS or parametric carbon tube (ties to #57).
