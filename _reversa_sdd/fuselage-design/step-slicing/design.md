# step-slicing — Technical Design

> Use-case design, nested under module [`fuselage-design`](../design.md).
> Focuses on HOW this slice is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Module endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/fuselage_slice_service.py` 🟢

```python
slice_step_file(
    file_content,
    filename,
    number_of_slices: int = 50,
    points_per_slice: int = 30,
    slice_axis: str = "auto",
    fuselage_name: str = "Imported Fuselage",
) -> FuselageSliceResponse          # l.28-116
```

### Route owned by this slice 🟢

| Method | Path | Handler | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `/slice` | `fuselage_slice.py:18` | multipart upload, `.step` / `.stp` | `FuselageSliceResponse` | 200 · **422 wrong extension** · **500 no CadQuery** · 500 |

This route is **standalone** — it is not nested under an aeroplane and persists
nothing. It returns a `FuselageSchema` the caller may then `PUT` through
[`superellipse-xsecs/`](../superellipse-xsecs/design.md). 🟢

### Geometry surface — `cad_designer/aerosandbox/slicing.py` (1339 l.) 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `slice_step_to_fuselage` | top-level STEP → xsec stack | — |
| arc-length point weighting | contour resampling | l.116-152 |
| `select_outer_contour` | picks the cluster enclosing the axis | l.207-267 |
| `_curvature_density` | the station-placement metric | l.347 |
| `adaptive_x_stations` | curvature-driven station placement | l.375 |
| solid/shell cut | `Workplane.split(keepTop=True)` vs `BRepAlgoAPI_Section` | l.476-489 |
| superellipse `r(θ)` | polar radius | l.585-586 |
| `perimeter(a,b,n)` | `quad` integral, `limit=200` | l.588-598 |
| `area(a,b,n)` | closed-form Γ expression | l.600-602 |
| `polygon_area` | shoelace over the sliced outline | l.604-608 |
| `fit_symmetric_superellipse` | **the fuselage fit** | l.610-661 |
| `fit_superellipse` | asymmetric variant, **unused here** | l.663 |

### Output shape 🟢

`FuselageSliceResponse` — significant fields:

| Field | Type | Meaning |
|---|---|---|
| (fuselage) | `FuselageSchema` | the fitted superellipse stack |
| `volume_ratio` | float | reconstructed loft volume ÷ original solid volume |
| `area_ratio` | float | reconstructed surface area ÷ original |
| `original_tessellation_url` | `null` | hard-coded `None` — STL export not wired (l.113-115) |
| `reconstructed_tessellation_url` | `null` | idem |

## Main Flow

### F1 — `slice_step_file` (l.28-116) 🟢

1. **Lazy-import** `cad_designer.aerosandbox.slicing.slice_step_to_fuselage`
   (l.42-48). CadQuery is not available on every platform, so an `ImportError`
   here becomes an `InternalError` → 500 rather than a start-up failure
   (ADR 0017).
2. Validate the extension is `.step` or `.stp`; otherwise reject **before** any
   filesystem access.
3. Reduce `filename` to its **basename**, build the temp path, and verify it with
   `is_relative_to` before writing — the explicit path-traversal guard
   (S2083, l.50-64).
4. Write the upload into a temporary directory and slice it (F2).
5. `rmtree` the temporary directory in a **`finally`** block, whatever happened.
6. Sanitise `NaN` / `Inf` in the result to `None` (GH#301).
7. Build the `FuselageSchema` plus the fidelity metrics and return
   `FuselageSliceResponse`.

`original_tessellation_url` and `reconstructed_tessellation_url` are hard-coded
`None` with a comment that STL export is not wired yet (l.113-115).

The work is documented as CPU-bound, **5–30 s**. 🟢

### F2 — Slicing internals (`slicing.py`) 🟢

1. **Station placement.** `adaptive_x_stations` (l.375) distributes the requested
   `number_of_slices` along the body driven by `_curvature_density` (l.347), so
   shoulders and tail cones get more stations than a parallel mid-body.
2. **Cutting.** A solid is cut with `Workplane.split(keepTop=True)`; a shell
   falls back to `BRepAlgoAPI_Section` (gh-727, l.476-489).
3. **Contour selection.** A plane may produce several disjoint loops;
   `select_outer_contour` (l.207-267) keeps the cluster that **encloses the
   longitudinal axis**.
4. **Resampling.** Points along the contour are weighted by arc length
   (l.116-152) so the fit is not biased toward densely tessellated regions.
   `points_per_slice` (default 30) sets the sample count.
5. **Fitting.** `fit_symmetric_superellipse` per station (F3).
6. **Fidelity.** The reconstructed superellipse loft is compared against the
   original solid to produce `volume_ratio` and `area_ratio`.

### F3 — Superellipse fit (`fit_symmetric_superellipse`, l.610-661) 🟢

```
Shape law (cross-section plane, Y lateral, Z vertical):
    |y/a|^n + |z/b|^n = 1

Polar form actually evaluated:
    r(θ) = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)            (l.585-586)

Derived:
    perimeter(a,b,n) = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ   (quad, limit=200)  (l.588-598)
    area(a,b,n)      = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)                      (l.600-602)
    polygon_area     = shoelace over the sliced outline                     (l.604-608)
```

Procedure:

1. Force the centre onto the Z axis: `center = [0, mean(z)]`.
2. Shift the points, convert to `(θ, r)`, then **mirror** them (`θ → −θ`, same
   `r`) to enforce left/right symmetry.
3. Minimise

   ```
   radius_loss = mean( (r_i − r_fit(θ_i))² )
   length_loss = (perimeter_fit − perimeter_actual)²
   objective   = radius_loss + 0.01 · length_loss
   ```

4. `scipy.optimize.minimize`, method **`L-BFGS-B`**,
   `x0 = [1.0, 1.0, initial_n = 2.0]`, bounds `a, b ∈ (1e-3, ∞)`,
   **`n ∈ [0.5, 8.0]`**.

The `0.01` perimeter weight and the `n` bounds are the two magic numbers of the
pipeline: the weight keeps the fit from matching radii while drifting in
circumference, and the bounds stop the optimiser from degenerating into a cross
(`n < 0.5`) or a hard rectangle (`n > 8`).

The asymmetric `fit_superellipse` (l.663) exists in the same module but is **not**
the fuselage path — do not wire it in. 🟢

### F4 — Output units — mechanism decided, not yet implemented (`Q-FD-2`) 🟢

The fitted `a` and `b` are **Y and Z half-axes**, matching
[`superellipse-xsecs/`](../superellipse-xsecs/design.md) in *shape*; `n` is
dimensionless. There is no unit conversion in this slice — the response is
directly `PUT`-able.

**Confirmed, and now answered by the maintainer (2026-08-13).** The
reviewer's finding stands as fact: `slice_step_to_fuselage`
(`cad_designer/aerosandbox/slicing.py:856-865`) takes `step_path`,
`number_of_slices`, `points_per_slice`, `slice_axis`, `fuselage_name`,
`adaptive`, `curvature_weight` — **no scale or unit parameter** — and
`app/services/fuselage_slice_service.py` contains no `scale`, `0.001` or `1000`
anywhere. The emitted `a` / `b` / `xyz` are therefore the STEP's **native**
coordinate values, verbatim.

That is safe on the `openvsp-import` path only because
[`openvsp-import` BR-OV13](../../openvsp-import/requirements.md) forces
`STEPSettings.LenUnit = LEN_M` on every export. On the **user-upload** path
(`POST /fuselages/slice`) nothing constrains the unit, and millimetres are the
normal CAD authoring convention — the same convention `cad_designer` itself uses
per [ADR 0001](../../adrs/0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md).
A millimetre-authored STEP therefore yields a fuselage **1000× too large**,
stored as metres, with no error and no warning. `volume_ratio` / `area_ratio`
(BR-F11) do **not** catch it: both are ratios of reconstruction to original, so
they stay ≈1.0 under a uniform scale error — this is the most reachable
silent-1000× path in the system.

**Decided mechanism: unify across both upload paths (this one, and the
`construction-parts` STEP importer, which assumes the opposite unit) —
header detection + explicit override + a plausibility check.** No single
layer is reliable alone:

1. **Read the unit from the STEP header** — the `SI_UNIT` entries in
   `GEOMETRIC_REPRESENTATION_CONTEXT` are standard and usually correct.
2. **Explicit override at upload**, pre-filled with the detected value —
   necessary because the project's own RV-7 test fixture was found during the
   interview to carry **contradictory** `SI_UNIT` declarations.
3. **Plausibility check on the resulting absolute dimensions**, emitting a
   `DesignWarning` when implausible. This layer needs no header at all: an RC
   fuselage is 0.3–3 m, so 1700 m or 1.7 mm is unambiguous — and it is the
   only layer that can catch a uniform scale error at all, since
   `volume_ratio` / `area_ratio` cancel it out by construction.

Storage stays metres; conversion happens at import. Not yet implemented.

## Alternative Flows

- **Non-STEP upload:** rejected before the temp file is created → 422. 🟢
- **Traversal filename:** reduced to its basename; the resolved path is checked
  with `is_relative_to` and the write is refused if it escapes. 🟢
- **Slice failure mid-way:** the `finally` block still removes the temp
  directory; the error propagates as an `InternalError` → 500. 🟢
- **Non-finite fit result:** sanitised to `None` rather than emitted as `NaN`
  (GH#301). 🟢
- **CadQuery absent:** the lazy import fails and the service raises
  `InternalError` → 500; every other route keeps working (ADR 0017). 🟢
- **Shell instead of solid:** `Workplane.split(keepTop=True)` is not applicable,
  so the code falls back to `BRepAlgoAPI_Section` (gh-727). 🟢
- **Multi-loop cutting plane:** `select_outer_contour` keeps the loop enclosing
  the longitudinal axis and discards the rest. 🟢
- **Optimiser hits a bound:** `n` is clamped to `[0.5, 8.0]` by the bounds
  themselves; no warning is emitted today. 🟢 CONFIRMED current behaviour —
  **decided to change** (`Q-FD-4`): a per-station `DesignWarning`
  `severity="info"` naming the station and the bound, escalating to
  `severity="warning"` above 25 % of stations. Not yet implemented.
- **Fewer than two usable slices: confirmed defect, not a documentation gap**
  (`Q-FD-6` bundle, resolved by code lookup). Three separate gates drop
  stations after cutting (`slicing.py:958-960, 987-993, 544-547`), and
  nothing between the loop and the return asserts `len(xsec_dicts) >= 2`;
  `slice_step_file` does not check either. A degenerate body returns **HTTP
  200 with 0 or 1 xsecs** and fails only later, on the caller's `PUT`, against
  `min_length=2`. The CUSTOM OpenVSP handler already enforces exactly this
  invariant (`app/converters/openvsp_custom_handler.py:98-106`); this
  pipeline should assert it explicitly at slice time instead of deferring the
  failure. 🟢

## Dependencies

- **CadQuery / OCCT** (optional) — the geometry kernel; lazy-imported, absence
  yields a clean 500 (ADR 0017).
- **SciPy** — `optimize.minimize` (`L-BFGS-B`) for the fit and `integrate.quad`
  for the perimeter.
- **`cad_designer/aerosandbox/slicing.py`** — the whole geometric pipeline
  (read-only layer, ADR 0002).
- **[`superellipse-xsecs/`](../superellipse-xsecs/design.md)** — the *consumer*
  of this slice's output, reached only through a subsequent `PUT` by the caller;
  there is no direct call between them.
- **`app/schemas/aeroplaneschema.py`** — `FuselageSchema` /
  `FuselageXSecSuperEllipseSchema` define the output shape.

Notably **not** a dependency: `aeroplane-core`. This route takes no aeroplane
UUID and touches no database. 🟢

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The slice route is standalone and persists nothing — the caller decides whether to store the result | `app/api/v2/endpoints/fuselage_slice.py:18`; no DB access in `slice_step_file` | 🟢 |
| The geometry kernel is lazy-imported so the API starts without it | `fuselage_slice_service.py:42-48`; ADR 0017 | 🟢 |
| The extension is checked **before** any filesystem access, not after writing | `fuselage_slice_service.py:28-116` | 🟢 |
| Path traversal is guarded explicitly at the upload boundary rather than trusted from the client | `fuselage_slice_service.py:50-64` (S2083) | 🟢 |
| Cleanup is a `finally` block, so a mid-slice failure cannot leak a temp directory | `fuselage_slice_service.py` (slice flow) | 🟢 |
| Non-finite values become `null` rather than propagating as invalid JSON | `fuselage_slice_service.py` (GH#301) | 🟢 |
| The response reports its own fidelity instead of asserting correctness | `fuselage_slice_service.py:113-115` | 🟢 |
| The fit is forced symmetric by mirroring the sample points, not by constraining the optimiser | `slicing.py:610-661` | 🟢 |
| The centre is pinned to the Z axis rather than fitted | `slicing.py:610-661` | 🟢 |
| The objective blends radius and perimeter error with a fixed `0.01` weight | `slicing.py:610-661` | 🟢 |
| The exponent is bounded to `[0.5, 8.0]` rather than left free | `slicing.py:610-661` | 🟢 |
| Slice stations are curvature-adaptive, not uniform | `slicing.py:347, 375` | 🟢 |
| The outer contour is selected by axis enclosure rather than by area | `slicing.py:207-267` | 🟢 |
| Contour points are weighted by arc length so tessellation density does not bias the fit | `slicing.py:116-152` | 🟢 |
| Solids and shells take different cutting paths | `slicing.py:476-489` (gh-727) | 🟢 |
| The asymmetric fit exists but is deliberately not the fuselage path | `slicing.py:663` | 🟢 |

## Internal State

The slice is **stateless and non-persistent**. It owns no table and writes no
row.

Transient state, for the duration of one request only:

- The temporary directory holding the uploaded STEP, guaranteed removed in a
  `finally` block.
- The in-memory contour set, the per-station fit results, and the reconstructed
  loft used to compute `volume_ratio` / `area_ratio`.

Everything the caller keeps must be re-submitted through
[`superellipse-xsecs/`](../superellipse-xsecs/design.md). 🟢

## Observability

- Slicing failures surface as `InternalError` → 500 with the shared error
  envelope; `logger.exception` is emitted by the endpoint layer. 🟢
- The slice response is itself the primary observability surface:
  `volume_ratio` / `area_ratio` tell the caller how good the simplification is
  (ADR 0012 in spirit — report, do not silently accept); **decided to become
  graded `DesignWarning`s** rather than plain numbers (`Q-FD-4`, see "Fidelity
  thresholds" in `../requirements.md`). Not yet implemented. 🟢
- **Decided to change (`Q-FD-5`):** no metrics, traces or progress events
  exist for the 5–30 s slice today; the fix is the task-model migration (202
  + status endpoint), which is where progress and cancellation land. Not yet
  implemented. 🟢
- **Decided to change (`Q-FD-4`):** no warning is emitted today when the
  optimiser lands on an `n` bound; a per-station `info`, escalating to
  `warning` above 25 % of stations, is decided. Not yet implemented. 🟢

## Risks and Gaps

All open questions below were put to the maintainer and answered
2026-08-13 → 2026-08-15 (`Q-FD-2` through `Q-FD-8b`, `Q-FD-6` bundle). Nothing
remains 🔴 in this slice; each item is decided direction, most not yet
implemented.

- 🟢 **Fidelity thresholds are decided** (`Q-FD-4`) — see "Fidelity
  thresholds" in `../requirements.md` for the full band table. Not yet
  implemented.
- 🟢 **A bound-hitting `n` is decided to warn** (`Q-FD-4`) — `info` per
  station, `warning` above 25 % of stations. Not yet implemented.
- 🟢 **`number_of_slices` and `points_per_slice` are already bounded — the
  earlier "no clamp found" claim was wrong** (`Q-FD-6` bundle, resolved by
  code lookup): `Form(ge=2, le=500)` and `10 ≤ … ≤ 200` at the HTTP boundary
  (`fuselage_slice.py:25-30`), plus an internal `min(…, 4096)` clamp on the
  shell/adaptive station path (`slicing.py:951`, no equivalent clamp on the
  solid path). These bound the **station count**, not the sections that
  survive filtering — see the next item.
- 🟢 **A 5–30 s slice is decided to join the task model** (`Q-FD-5`): `202`
  plus a status endpoint plus a timeout. Not yet implemented — see
  `../contracts.md`.
- 🟢 **Fewer than two usable slices are confirmed NOT guaranteed — a real
  defect** (`Q-FD-6` bundle, resolved by code lookup): three separate gates
  drop stations after cutting (`slicing.py:958-960, 987-993, 544-547`) and
  nothing asserts `len(xsec_dicts) >= 2` before returning; the OpenVSP CUSTOM
  handler already enforces this invariant elsewhere
  (`openvsp_custom_handler.py:98-106`) — this pipeline is missing it.
- 🟢 **`slice_axis="auto"` behaviour is now confirmed** (`Q-FD-6` bundle,
  resolved by code lookup): `detect_longest_axis`
  (`slicing.py:470-473, 892-904`), a pure bounding-box comparison, so a short,
  wide body (a flying-wing pod) is sliced across its span with no warning.
  Alternatives are `"x"` (no-op), `"y"` (rotate +90° about Z), `"z"` (rotate
  −90° about Y); anything else raises, and the endpoint pre-validates the
  four literals with a 422 (`fuselage_slice.py:44-48`), so that branch is
  defence-in-depth.
- 🟢 **A second, unrelated STEP→fuselage path is confirmed dead, not merely
  suspected** (`Q-FD-8`, `P-DEAD-0` rule 3).
  `FuselageConfiguration.from_step_file` (`FuselageConfiguration.py:114-140`)
  assigns `analysis_specific_options = {dict(...)}` — a set containing an
  unhashable dict — which raises `TypeError` on every execution, so the path
  has never run. It is **not** used by this slice, and its removal is
  recorded in `../requirements.md`, not executed (ADR 0002 freeze). This
  module owns exactly one working STEP ingestion route: this one.
