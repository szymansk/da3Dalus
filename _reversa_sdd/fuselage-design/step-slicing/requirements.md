# step-slicing

> Use-case specification, nested under module [`fuselage-design`](../requirements.md).
> Focuses on WHAT this slice does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: fuselage-design,
> `_reversa_sdd/data-dictionary.md` §Module: fuselage-design.

## Overview

`step-slicing` is **one of two peer ways** to populate a fuselage's
cross-section stack — the automated one, converting precise geometry into the
parametric model. (The other is direct authoring, addressed in
[`superellipse-xsecs/`](../superellipse-xsecs/requirements.md); see
`Q-FD-8b` in the module overview.) It accepts an uploaded STEP file, cuts it
into cross-section contours along the body axis, fits a symmetric
superellipse to each contour, and returns the resulting stack **together with
its own fidelity metrics**. It persists nothing — the caller decides whether
to `PUT` the result under an aeroplane. 🟢

⚠ **Contract change decided, not yet implemented (`Q-FD-5`):** `POST /slice`
currently returns `200` synchronously after 5–30 s of CPU-bound work. It is
decided to join the task model — `202 Accepted` plus a status endpoint, plus
a timeout — like every other long CAD operation in the system. See "Pending
Gaps" → "Decided, Not Yet Implemented" in [`tasks.md`](tasks.md).

## Responsibilities

- Accept a STEP upload, validate it and guard the filesystem boundary. 🟢
- Cut the solid (or shell) into contours at adaptively chosen stations. 🟢
- Select the correct contour when a cutting plane yields several loops. 🟢
- Fit a symmetric superellipse `(a, b, n)` to each contour. 🟢
- Report the reconstruction fidelity (`volume_ratio`, `area_ratio`) so the caller
  can judge the simplification. 🟢
- Fail cleanly and leave no temporary state behind, on every path. 🟢

**Explicitly NOT this slice's responsibility:** persisting the result
(→ [`superellipse-xsecs/`](../superellipse-xsecs/requirements.md), via a
subsequent `PUT`); producing `step_path` / `solid_step_path` (→ `openvsp-import`
gh-729 and `openvsp_solid_sewing_service` gh-731); STL/tessellation export (not
wired).

## Business Rules

| Rule | Derived from | Statement |
|---|---|---|
| **BR-F3** | module BR-F3 | The polar form is what the fit evaluates 🟢 |
| **BR-F6** | module BR-F6 | The fit is symmetric by construction 🟢 |
| **BR-F7** | module BR-F7 | The objective blends radius error with perimeter error 🟢 |
| **BR-F8** | module BR-F8 | Only `.step` / `.stp` uploads are accepted 🟢 |
| **BR-F9** | module BR-F9 | Path traversal is explicitly guarded (S2083) 🟢 |
| **BR-F10** | module BR-F10 | Non-finite fit results are sanitised to `null` (GH#301) 🟢 |
| **BR-F11** | module BR-F11 | The response carries its own quality metric 🟢 |
| **BR-F12** | module BR-F12 | The geometry kernel is optional and lazy-imported 🟢 |
| **BR-F13** | module BR-F13 | Slicing is CPU-bound and slow (5–30 s) 🟢 |
| **BR-F14** | module BR-F14 | The outer contour is the one enclosing the longitudinal axis 🟢 |
| **BR-F15** | module BR-F15 | Stations are chosen adaptively by curvature 🟢 |
| **BR-F16** | module BR-F16 | Solids and shells are cut differently 🟢 |

### BR-F8 — Extension whitelist 🟢

Only `.step` and `.stp` are accepted, and the check happens **before anything is
written to disk** (`app/services/fuselage_slice_service.py:28-116`).

### BR-F9 — Path-traversal guard (S2083) 🟢

The uploaded filename is reduced to its **basename**, and the resolved temp path
is checked with `is_relative_to` before writing (l.50-64). The temp directory is
always removed in a `finally` block.

### BR-F12 — Optional geometry kernel 🟢

`cad_designer.aerosandbox.slicing.slice_step_to_fuselage` is **lazy-imported**;
when CadQuery is unavailable (e.g. `linux/aarch64`) the service raises
`InternalError` at call time instead of failing at module import
(l.42-48, ADR 0017).

### BR-F15 — Adaptive stations 🟢

`adaptive_x_stations` (`cad_designer/aerosandbox/slicing.py:375`) places more
slices where a `_curvature_density` metric (l.347) is high, rather than
uniformly. Point weighting along each contour is by **arc length** (l.116-152),
so a densely tessellated edge does not bias the fit.

### BR-F14 — Outer-contour selection 🟢

A slice plane can cut several disjoint loops (internal structure, wheel wells);
`select_outer_contour` picks the cluster that **encloses the longitudinal axis**
(l.207-267).

### BR-F16 — Solid vs shell 🟢

A solid is cut with `Workplane.split(keepTop=True)`; a shell falls back to
`BRepAlgoAPI_Section` (gh-727, l.476-489).

### BR-F6 / BR-F7 — The symmetric superellipse fit 🟢

`fit_symmetric_superellipse` (`slicing.py:610-661`) is the one used for
fuselages; the asymmetric `fit_superellipse` (l.663) exists but is **not** the
fuselage path.

1. The centre is **forced onto the Z axis**: `center = [0, mean(z)]`.
2. Points are shifted, converted to `(θ, r)`, then **mirrored**
   (`θ → −θ`, same `r`) to enforce left/right symmetry.
3. Objective minimised over `(a, b, n)`:

```
radius_loss = mean( (r_i − r_fit(θ_i))² )
length_loss = (perimeter_fit − perimeter_actual)²
objective   = radius_loss + 0.01 · length_loss
```

4. `scipy.optimize.minimize`, method **`L-BFGS-B`**,
   `x0 = [1.0, 1.0, initial_n = 2.0]`, bounds `a, b ∈ (1e-3, ∞)`,
   **`n ∈ [0.5, 8.0]`**.

The `0.01` perimeter weight and the `n` bounds are the two magic numbers of the
fuselage pipeline: the weight keeps the fit from matching radii while drifting in
circumference, and the bounds stop the optimiser from degenerating into a cross
(`n < 0.5`) or a hard rectangle (`n > 8`).

Evaluated forms (BR-F3):

```
r(θ)             = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)                (l.585-586)
perimeter(a,b,n) = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ   (scipy quad, limit=200) (l.588-598)
area(a,b,n)      = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)                          (l.600-602)
polygon_area     = shoelace formula over the sliced outline                 (l.604-608)
```

### BR-F10 / BR-F11 — Honest output 🟢

`NaN` / `Inf` in the response are replaced by `None` rather than emitted as
invalid JSON (GH#301). `volume_ratio` and `area_ratio` compare the reconstructed
superellipse loft against the original solid, so the caller can judge whether the
simplification is acceptable. `original_tessellation_url` and
`reconstructed_tessellation_url` are hard-coded `None` — STL export is not wired
yet (`fuselage_slice_service.py:113-115`).

### Fidelity thresholds — decided, not yet implemented (`Q-FD-4`) 🟢

`volume_ratio` / `area_ratio` are currently *reported* but never *judged*.
Answered by expert consensus, endorsed by the maintainer 2026-08-14:

| Band | Range | Effect |
|---|---|---|
| Good | `[0.95, 1.05]` | silent |
| Degraded | `[0.85, 0.95) ∪ (1.05, 1.15]` | `DesignWarning` `severity="info"` |
| Poor | `[0.70, 0.85) ∪ (1.15, 1.40]` | `DesignWarning` `severity="warning"` |
| Reject | outside `[0.70, 1.40]`, or `volume_ratio ≤ 0.05`, or non-finite | the slice is **rejected**, not returned |

Calibrated on fuselage parasite drag at RC/UAV scale (Sadraey Eq. 7.5): a 5 %
`area_ratio` error is roughly a 5 % `C_D0,f` error, and the fuselage carries
15–30 % of a typical model's parasite drag — so a 5 % error there is ~1 %
aircraft `C_D0`, inside the Reynolds-driven scatter at this scale. The
`1.40` upper cut is deliberately below `4.0` so it also catches `Q-FD-3`'s
`a ↔ b` swap failure mode as a second line of defence. The `≤ 0.05` /
non-finite cut catches the degenerate-dimension case that already produced
`NaN` inside AeroBuildup's `log10` on a real fuselage.

**A bound-hitting exponent must also warn.** `n` clamped at `[0.5, 8.0]` by
the optimiser bounds (`slicing.py:1285`) sits *at* the bound silently today —
the opposite of ADR 0012. Emit a per-station `DesignWarning`
`severity="info"` naming the station and the bound; escalate to
`severity="warning"` once more than 25 % of stations hit a bound — past that
the superellipse family is the wrong model for the body.

Confidence: medium-high — the reject cuts and the failure-mode analysis are
solid; the internal `0.95` / `0.85` / `0.70` edges are engineering judgement
calibrated on the drag sensitivity above, to be tightened once ratio
statistics exist over a real corpus. Full reasoning:
[`../../expert-consensus-aero.md`](../../expert-consensus-aero.md).

## Functional Requirements

| ID | Refines | Requirement | Priority | Acceptance criterion |
|----|---------|-------------|----------|----------------------|
| RF-11 | module RF-11 | Slice an uploaded STEP into superellipse cross-sections | Must | `POST /slice` with a `.step` file → 200 `FuselageSliceResponse` containing a `FuselageSchema` |
| RF-12 | module RF-12 | Reject a non-STEP upload before touching the filesystem | Must | A `.stl` upload → 422; no temp file is created |
| RF-13 | module RF-13 | Report reconstruction fidelity with every slice result | Must | The response carries `volume_ratio` and `area_ratio` |
| RF-14 | module RF-14 | Sanitise non-finite fit values to `null` | Must | A degenerate slice yields `null`, never `NaN`, in the JSON body |
| RF-15 | module RF-15 | Always remove the temp directory, including on failure | Must | After a slice that raises, no temp directory remains |
| RF-16 | module RF-16 | Fail cleanly when the geometry kernel is absent | Must | Without CadQuery, `POST /slice` → 500 `internal_error`; the API still starts |
| RF-17 | module RF-17 | Fit a symmetric superellipse per slice with the documented objective and bounds | Must | Given a known ellipse outline, the fit returns `n ≈ 2` and `(a, b)` within tolerance |
| RF-18 | module RF-18 | Choose slice stations adaptively by curvature | Should | A body with a sharp shoulder receives more stations there than in the parallel mid-body |
| RF-19 | module RF-19 | Select the contour enclosing the longitudinal axis when a plane cuts several loops | Should | A slice through a wheel well returns the outer skin, not the well |
| RF-20 | module RF-20 | Handle both solid and shell STEP input | Should | A shell input falls back to `BRepAlgoAPI_Section` and still produces contours |
| RF-X2 | new (slice-local) | Guard the upload path against traversal (S2083) | Must | An upload named `"../../etc/passwd.step"` writes only to `<tmp>/passwd.step` |
| RF-X3 | new (slice-local) | Persist nothing | Must | A successful slice writes no database row |
| RF-X4 | new (slice-local) | Weight contour points by arc length before fitting | Should | A contour with one heavily refined edge fits the same `(a, b, n)` as its uniformly tessellated equivalent |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | Uploaded filenames are reduced to their basename and the resolved temp path is verified with `is_relative_to` before any write (path-traversal guard, S2083) | `app/services/fuselage_slice_service.py:50-64` | 🟢 |
| Security | Only `.step` / `.stp` extensions are accepted, checked before any filesystem access | `fuselage_slice_service.py:28-116` | 🟢 |
| Reliability | The temp directory is removed in a `finally` block regardless of outcome | `fuselage_slice_service.py` (slice flow) | 🟢 |
| Correctness | Non-finite fit outputs are converted to `None` so the response is always valid JSON | `fuselage_slice_service.py` (GH#301) | 🟢 |
| Correctness | The response carries its own fidelity metrics rather than asserting the fit is good | `fuselage_slice_service.py:113-115` | 🟢 |
| Correctness | The fit is forced left/right symmetric by mirroring the samples, and the centre is pinned to the Z axis | `cad_designer/aerosandbox/slicing.py:610-661` | 🟢 |
| Correctness | The exponent is bounded to `[0.5, 8.0]`, preventing degenerate cross or rectangle fits | `slicing.py:610-661` | 🟢 |
| Correctness | Contour points are weighted by arc length so tessellation density does not bias the fit | `slicing.py:116-152` | 🟢 |
| Performance | Slicing is documented CPU-bound work of **5–30 s**; the caller must expect a long request | `fuselage_slice_service.py` docstring | 🟢 |
| Performance | Slice stations are placed adaptively by curvature density rather than uniformly | `slicing.py:347, 375` | 🟢 |
| Portability | The geometry kernel is lazy-imported; its absence yields `InternalError` at call time, not an import-time crash | `fuselage_slice_service.py:42-48` (ADR 0017) | 🟢 |

## Acceptance Criteria

```gherkin
Feature: STEP slicing

  Scenario: A STEP solid becomes a superellipse stack
    Given a valid .step file describing a single closed fuselage solid
    When I POST /slice with number_of_slices 50 and points_per_slice 30
    Then the response status is 200
    And the payload contains a FuselageSchema with at least two cross-sections
    And volume_ratio and area_ratio are reported
    And no temp directory remains on disk

  Scenario: The slice persists nothing
    Given a valid .step file
    When I POST /slice with it
    Then the response status is 200
    And no fuselages row was created
    And no fuselage_xsecs row was created

  Scenario: A non-STEP upload is rejected before any write
    Given a file named model.stl
    When I POST /slice with it
    Then the response status is 422
    And no temp file was created

  Scenario: A traversal filename cannot escape the temp directory
    Given a file named "../../etc/passwd.step"
    When I POST /slice with it
    Then the write target is the basename inside the temp directory
    And the request does not touch any path outside it

  Scenario: The temp directory is removed even when slicing fails
    Given a .step file that makes the slicer raise
    When I POST /slice with it
    Then the response status is 500
    And no temp directory remains on disk

  Scenario: A degenerate slice yields null, not NaN
    Given a slice whose fit does not converge to finite values
    When the response is built
    Then the affected fields are null
    And the body is valid JSON

  Scenario: Slicing without a geometry kernel fails cleanly
    Given CadQuery is not installed
    When I POST /slice with a valid .step file
    Then the response status is 500
    And the error code is "internal_error"
    And the application is still serving other routes

Feature: Superellipse fitting

  Scenario: A circular outline fits an ellipse exponent
    Given a contour sampled from a circle of radius 0.1 m
    When fit_symmetric_superellipse runs
    Then n is approximately 2.0
    And a and b are both approximately 0.1

  Scenario: The exponent stays inside its bounds
    Given a contour that is very close to a rectangle
    When the fit runs
    Then n is at most 8.0
    And n is at least 0.5

  Scenario: The fit is symmetric even for an asymmetric contour
    Given a contour that is wider on the port side than the starboard side
    When the fit runs
    Then the fitted centre lies on the Z axis
    And the fitted shape is left/right symmetric

  Scenario: The perimeter term influences the fit
    Given a contour whose radii match one candidate but whose circumference matches another
    When the objective is evaluated
    Then it equals radius_loss plus 0.01 times length_loss

Feature: Slicing internals

  Scenario: Stations concentrate where curvature is high
    Given a body with a sharp shoulder and a long parallel mid-body
    When adaptive stations are chosen for a fixed total count
    Then more stations fall on the shoulder than on the mid-body

  Scenario: A multi-loop slice returns the outer skin
    Given a slice plane that cuts both the outer skin and a wheel well
    When the outer contour is selected
    Then the returned loop encloses the longitudinal axis

  Scenario: A shell input still produces contours
    Given a .step file containing a shell rather than a closed solid
    When it is sliced
    Then the section fallback is used
    And contours are produced

  Scenario: Tessellation density does not bias the fit
    Given two contours of the same shape, one with a heavily refined edge
    When both are fitted
    Then the fitted a, b and n agree within tolerance
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The slice pipeline itself (RF-11 / RF-17) | Must | The only automated route from imported geometry to a parametric fuselage; hand-authoring an xsec stack is the only alternative |
| Upload validation and the traversal guard (RF-12 / RF-X2) | Must | The only route in the whole module that accepts a file from the client |
| Temp-directory cleanup (RF-15) | Must | Slicing runs 5–30 s and can fail mid-way; leaked directories accumulate silently |
| Non-finite sanitisation (RF-14) | Must | Without it the response is invalid JSON and the caller cannot even read the error |
| Fidelity metrics (RF-13) | Must | The response is a *simplification*; without `volume_ratio` / `area_ratio` the caller cannot judge it (ADR 0012 in spirit) |
| Graceful failure without CadQuery (RF-16) | Must | The service must start on `linux/aarch64` (ADR 0017) |
| Persisting nothing (RF-X3) | Must | Keeps the slice idempotent and free of partial state; the caller owns the decision to store |
| Symmetric fit with pinned centre and bounded `n` (BR-F6 / BR-F7) | Must | An unbounded fit degenerates into a cross or a rectangle, and an unpinned centre drifts off the symmetry plane |
| Adaptive station placement (RF-18) | Should | Improves fidelity per slice; a uniform stack still produces a usable body |
| Outer-contour selection (RF-19) | Should | Only matters for bodies with internal loops, but silently wrong when it does |
| Arc-length point weighting (RF-X4) | Should | Removes a tessellation-dependent bias; the fit still converges without it |
| Shell fallback via `BRepAlgoAPI_Section` (RF-20) | Should | Solids are the normal input; shells are the gh-727 edge case |
| A fidelity threshold that rejects or flags a poor fit | Must | 🟢 Decided bands (`Q-FD-4`): silent / `info` / `warning` / reject on `volume_ratio` and `area_ratio`, plus a graded warning on a bound-hitting `n` — see "Fidelity thresholds" below. Not yet implemented |
| Progress, cancellation or an async job for the 5–30 s request | Could | 🟡 No streaming or job API exists |
| The asymmetric `fit_superellipse` (l.663) | Won't | Exists in the module but is not the fuselage path; do not wire it in |
| Tessellation URLs on the response | Won't | Hard-coded `None`; STL export is not wired |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/fuselage_slice_service.py` | `slice_step_file` (l.28-116), lazy import (l.42-48), traversal guard (l.50-64), tessellation URLs (l.113-115) | 🟢 |
| `app/api/v2/endpoints/fuselage_slice.py` | `POST /slice` (l.18) | 🟢 |
| `cad_designer/aerosandbox/slicing.py` (1339 l.) | `slice_step_to_fuselage`, superellipse `r`/`perimeter`/`area`/`polygon_area` (l.585-608), `fit_symmetric_superellipse` (l.610-661), `fit_superellipse` (l.663, unused here), `select_outer_contour` (l.207-267), `adaptive_x_stations` (l.375), `_curvature_density` (l.347), arc-length weighting (l.116-152), solid/shell cut (l.476-489) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `FuselageSchema` (l.755), `FuselageXSecSuperEllipseSchema` (l.711) — the output shape | 🟢 |
| `cad_designer/.../fuselage/FuselageConfiguration.py` | `from_step_file` (l.114-140) — a **separate** STEP path, confirmed dead code, not used by this slice; removal recorded in `../requirements.md`, not executed (`Q-FD-8`, `P-DEAD-0`) | 🟢 |
