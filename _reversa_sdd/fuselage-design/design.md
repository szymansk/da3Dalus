# fuselage-design — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`superellipse-xsecs/`](superellipse-xsecs/),
> [`step-slicing/`](step-slicing/).

## Interface

### Service surface — `app/services/fuselage_service.py` (403 l.) 🟢

| Symbol | Signature | Returns | Line |
|---|---|---|---|
| `list_fuselage_names` | `(db, aeroplane_uuid)` | `list[str]` | l.45 |
| `create_fuselage` | `(db, aeroplane_uuid, name, payload)` | `FuselageModel` | l.63 |
| `update_fuselage` | `(db, aeroplane_uuid, name, payload)` | `FuselageModel` | l.103 |
| `get_fuselage` | `(db, aeroplane_uuid, name)` | `FuselageModel` | l.137 |
| `delete_fuselage` | `(db, aeroplane_uuid, name)` | `None` | l.160 |
| `get_fuselage_cross_sections` | `(db, aeroplane_uuid, name)` | `list[FuselageXSecSuperEllipseModel]` | l.193 |
| `delete_all_cross_sections` | `(db, aeroplane_uuid, name)` | `None` | l.219 |
| `get_cross_section` | `(db, …, index)` | xsec | l.244 |
| `create_cross_section` | `(db, …, payload)` | xsec | l.276 |
| `update_cross_section` | `(db, …, index, payload)` | xsec | l.327 |
| `delete_cross_section` | `(db, …, index)` | `None` | l.364 |

### Slicing surface — `app/services/fuselage_slice_service.py` 🟢

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

### Geometry surface — `cad_designer/aerosandbox/slicing.py` (1339 l.) 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `slice_step_to_fuselage` | top-level STEP → xsec stack | — |
| superellipse `r(θ)` | polar radius | l.585-586 |
| `perimeter(a,b,n)` | `quad` integral, `limit=200` | l.588-598 |
| `area(a,b,n)` | closed-form Γ expression | l.600-602 |
| `polygon_area` | shoelace over the sliced outline | l.604-608 |
| `fit_symmetric_superellipse` | **the fuselage fit** | l.610-661 |
| `fit_superellipse` | asymmetric variant, unused here | l.663 |
| `select_outer_contour` | picks the cluster enclosing the axis | l.207-267 |
| `adaptive_x_stations` | curvature-driven station placement | l.375 |
| `_curvature_density` | the driving metric | l.347 |
| arc-length point weighting | contour resampling | l.116-152 |
| solid/shell cut | `Workplane.split(keepTop=True)` vs `BRepAlgoAPI_Section` | l.476-489 |

### Data model 🟢

```
fuselages ──1:N (ordered by sort_index, cascade delete-orphan)──▶ fuselage_xsecs
```

`fuselages` (`FuselageModel`, `app/models/aeroplanemodel.py:526`):
`name` (required), `symmetric` (bool, **default `False`**),
`step_path` (str \| null, relative), `solid_step_path` (str \| null, relative),
`aeroplane_id` FK → `aeroplanes.id` `ON DELETE CASCADE`.

`fuselage_xsecs` (`FuselageXSecSuperEllipseModel`, `:512`):
`xyz` (JSON `[x,y,z]`, **metres**, the section centre), `a` (float, **Y
half-axis**, m), `b` (float, **Z half-axis**, m), `n` (float, exponent),
`sort_index` (int, default 0), `fuselage_id` FK `ON DELETE CASCADE`.

Schemas: `FuselageSchema` (`aeroplaneschema.py:755`) — `name`,
`x_secs: list[FuselageXSecSuperEllipseSchema]` with **`min_length=2`**,
`symmetric: bool = False`, `step_path: str | None = None`,
`solid_step_path: str | None = None`. `FuselageXSecSuperEllipseSchema` (l.711) —
`xyz`, `a`, `b`, `n`, all required, all metres except `n`. 🟢

## Main Flow

### F1 — Create a fuselage (`create_fuselage`, l.63) 🟢

1. Resolve the aeroplane by UUID (404 if absent).
2. Validate `FuselageSchema` — `x_secs` `min_length=2`.
3. A name already present on this aeroplane raises `ConflictError` → **409**
   (l.80-84). *This differs from `create_wing`, which raises `ValidationError` →
   422 for the same condition (`wing_service.py:285-289`).*
4. Persist the fuselage and its cross-sections in `sort_index` order.
5. Drive the component-tree auto-sync `sync_group_for_fuselage` (gh#108).
6. Return the model; `get_db()` commits (ADR 0009).

### F2 — Update a fuselage (`update_fuselage`, l.103) 🟢

The old `FuselageModel` is **removed from the collection and a brand-new one
appended** (l.120-122) — a destructive replace, not a field merge. **This is
current behaviour, not the target.** `step_path` and `solid_step_path` not
present in the incoming payload are lost today, because the replacement row is
built purely from the payload — and per `Q-FD-7` (answered by the maintainer,
2026-08-15) that is decided as a defect to fix, the same class as issue #1094
(`ComponentEditDialog` hard-coding `model_ref: null`): a partial update must
not destroy what it does not mention. The re-implementation preserves
`step_path` / `solid_step_path` when the payload omits them, rather than
requiring the caller to echo them back.

### F3 — Delete a fuselage (`delete_fuselage`, l.160) 🟢

1. Resolve and delete; the ORM cascade removes `fuselage_xsecs`.
2. `delete_synced_nodes("fuselage:<name>")` removes the component-tree group
   (l.179-181, gh#108).

### F4 — STEP slicing (`slice_step_file`, l.28-116) 🟢

**This flow describes today's synchronous `200`-with-body contract.** Per
`Q-FD-5` (answered by the maintainer, 2026-08-15), `POST /slice` is decided to
join the task model — `202 Accepted` with a task id, fetched from a status
endpoint, plus a timeout — like every other 5–30 s CAD operation in the
system. Not yet implemented; see `step-slicing/design.md` §F1 for the target
contract.

1. **Lazy-import** `cad_designer.aerosandbox.slicing.slice_step_to_fuselage`
   (l.42-48). CadQuery is not available on every platform, so an `ImportError`
   here becomes an `InternalError` → 500 rather than a start-up failure
   (ADR 0017).
2. Validate the extension is `.step` or `.stp`; otherwise reject **before** any
   filesystem access.
3. Reduce `filename` to its **basename**, build the temp path, and verify it with
   `is_relative_to` before writing — the explicit path-traversal guard (S2083,
   l.50-64).
4. Write the upload into a temporary directory and slice it.
5. `rmtree` the temporary directory in a **`finally`** block, whatever happened.
6. Sanitise `NaN` / `Inf` in the result to `None` (GH#301).
7. Build the `FuselageSchema` plus the fidelity metrics and return
   `FuselageSliceResponse`.

`original_tessellation_url` and `reconstructed_tessellation_url` are hard-coded
`None` with a comment that STL export is not wired yet (l.113-115).

### F5 — Slicing internals (`slicing.py`) 🟢

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
5. **Fitting.** `fit_symmetric_superellipse` per station (F6).
6. **Fidelity.** The reconstructed superellipse loft is compared against the
   original solid to produce `volume_ratio` and `area_ratio`.

### F6 — Superellipse fit (`fit_symmetric_superellipse`, l.610-661) 🟢

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

### F7 — Axis convention (gh-706) 🟢

```
a  (Y half-axis, semi-width)  → ASB FuselageXSec.width
b  (Z half-axis, semi-height) → ASB FuselageXSec.height
```

(`app/schemas/aeroplaneschema.py:711-723`.) They are **half-axes, not
diameters** — a consumer that treats them as full widths halves the body.

### F8 — Symmetry (gh-715) 🟢

`fuselages.symmetric` defaults to **`False`**, the opposite of
`wings.symmetric` (`True`). The main fuselage sits on the symmetry plane and
must not be mirrored. Paired sub-fuselages (landing-gear struts, wheel fairings,
engine cowlings) are stored **once** by OpenVSP and duplicated `y → −y` on the
fly by every downstream consumer — the ASB converter, the CAD builder and the
viewer (`aeroplanemodel.py:529-533`, `aeroplaneschema.py:762-773`).

### F9 — STEP artefacts 🟢

| Column | Written by | Content | Served by |
|---|---|---|---|
| `step_path` | `openvsp-import`, gh-729 | per-geom **Surface** STEP | `GET .../fuselages/{name}/step` (`fuselages.py:198`) |
| `solid_step_path` | `openvsp_solid_sewing_service`, gh-731 | sewed/healed closed **Solid** | `GET .../fuselages/{name}/solid_step` (`fuselages.py:234`) |

Both are **relative** paths resolved against `settings.ARTIFACTS_BASE_DIR`
(default `/tmp/da3dalus_artifacts`, always `.resolve()`d by a field validator,
`app/core/config.py:24-32`). `solid_step_path` is `None` when sewing failed or
the fuselage was never VSP-imported.

## Alternative Flows

- **Duplicate name:** `ConflictError` → **409** (`fuselage_service.py:80-84`).
  🟢 — the confirmed contract (`Q-FD-1`); `create_wing` is being aligned to
  409, not the reverse.
- **Fewer than two cross-sections:** rejected by `FuselageSchema`'s
  `min_length=2` → 422. 🟢
- **Missing artefact:** `GET .../step` or `.../solid_step` with a `NULL` column
  → 404. 🟡 INFERRED from the column nullability and the download route shape.
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
- **Multi-body STEP into `FuselageConfiguration.from_step_file`:** warns and uses
  only the first fuselage; raises `ValueError` when the conversion yields none.
  🟢 — but see the reachability gap below.

## Dependencies

- **`aeroplane-core`** — every route resolves an aeroplane by UUID first;
  `fuselages` cascade-delete with the aeroplane. Create/update/delete call back
  into `component_tree_service` (gh#108) — a two-way dependency broken by lazy
  imports.
- **`cad-designer-topology`** — `FuselageConfiguration` (millimetre world,
  frozen, ADR 0002).
- **`openvsp-import`** — the sole writer of `step_path` (gh-729) and, through
  `openvsp_solid_sewing_service`, of `solid_step_path` (gh-731).
- **`cad-generation`** — the consumer of `solid_step_path` for battery-bay cuts,
  servo-mount unions and carbon-tube bores.
- **`aero-analysis`** — consumes the xsec stack as the ASB fuselage model.
- **`app/core/config.py`** — `ARTIFACTS_BASE_DIR` resolution.
- **CadQuery / OCCT** (optional) — required by the slicing pipeline only.
- **SciPy** — `optimize.minimize` (`L-BFGS-B`) and `integrate.quad` for the fit.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Two **peer** representations coexist on purpose — parametric xsecs are a first-class authoring surface, not a view derived from STEP (`Q-FD-8b`) | `fuselage_service.py:63,103` (`x_secs` in create/update); `PropertyForm.tsx:24,529-532,575`; `code-analysis.md` §STEP vs superellipse | 🟢 |
| The superellipse is parameterised by **half-axes** mapped to ASB `width`/`height` | gh-706; `aeroplaneschema.py:711-723` | 🟢 |
| `symmetric` defaults to `False`, opposite to wings | gh-715; `aeroplanemodel.py:529-533` | 🟢 |
| The fit is forced symmetric by mirroring the sample points, not by constraining the optimiser | `slicing.py:610-661` | 🟢 |
| The objective blends radius and perimeter error with a fixed `0.01` weight | `slicing.py:610-661` | 🟢 |
| The exponent is bounded to `[0.5, 8.0]` rather than left free | `slicing.py:610-661` | 🟢 |
| Slice stations are curvature-adaptive, not uniform | `slicing.py:347, 375` | 🟢 |
| The outer contour is selected by axis enclosure rather than by area | `slicing.py:207-267` | 🟢 |
| The slice response reports its own fidelity instead of asserting correctness | `fuselage_slice_service.py:113-115` | 🟢 |
| Path traversal is guarded explicitly at the upload boundary | `fuselage_slice_service.py:50-64` | 🟢 |
| The geometry kernel is lazy-imported so the API starts without it | `fuselage_slice_service.py:42-48`; ADR 0017 | 🟢 |
| `update_fuselage` replaces rather than merges — **decided to change**: artefact pointers must be preserved when omitted (`Q-FD-7`) | `fuselage_service.py:120-122` | 🟢 |
| Duplicate fuselage name → 409, the confirmed contract; `create_wing` aligns to it | `fuselage_service.py:80-84` vs `wing_service.py:285-289` | 🟢 |

## Internal State

The module is stateless between requests. Persistent state:

- `fuselages` — name, the `symmetric` flag and the two artefact pointers.
- `fuselage_xsecs` — the superellipse stack `(xyz, a, b, n, sort_index)` in
  metres.
- Files under `ARTIFACTS_BASE_DIR` — the Surface and Solid STEP artefacts,
  referenced by relative path and **not** owned by this module's write paths.

Computed at read/slice time and never persisted: `volume_ratio`, `area_ratio`,
the fitted perimeter and area, and every mirrored copy implied by
`symmetric = true`.

Transient state: the temp directory of a slice request, guaranteed removed in a
`finally` block.

## Observability

- Slicing failures surface as `InternalError` → 500 with the shared error
  envelope; `logger.exception` is emitted by the endpoint layer. 🟢
- `FuselageConfiguration.from_step_file`'s multi-fuselage warning is **moot**:
  the factory is confirmed dead code (`Q-FD-8`) and is removed from the spec —
  it never executes, so this warning never fires either. 🟢
- The slice response is itself the primary observability surface:
  `volume_ratio` / `area_ratio` tell the caller how good the simplification is
  (ADR 0012 in spirit — report, do not silently accept); per `Q-FD-4` these
  ratios and a bound-hitting `n` also become graded `DesignWarning`s
  (`P-WARN-0`) rather than merely reported numbers. Not yet implemented. 🟢
- **Decided to change (`Q-FD-5`):** no metrics, traces or progress events
  exist today for the 5–30 s slice, and the client sees a single long
  request; the fix is the task-model migration (202 + status endpoint), which
  also supplies the missing progress/cancellation/timeout surface. Not yet
  implemented. 🟢

## Risks and Gaps

All open questions in this module were put to the maintainer and answered
2026-08-13 → 2026-08-15; what remains below is **decided direction not yet
implemented**, not open design questions.

- 🟢 **`FuselageConfiguration.from_step_file` is confirmed dead code, and is
  removed from the spec (`Q-FD-8`, `P-DEAD-0` rule 3).** It assigns
  `analysis_specific_options = {dict(panel_resolution=24,
  panel_spacing="cosine")}` — a **set containing a dict**
  (`FuselageConfiguration.py:123-125`), which is unhashable and raises
  `TypeError` on every execution, so the path has never run. Because
  `FuselageConfiguration.py` is inside the ADR 0002 freeze, the removal is
  stated here rather than executed. This does **not** mean the CAD side
  cannot be built from the parametric representation "at all" — the correct
  reading (`Q-FD-8b`) is that the xsecs are already a first-class authoring
  surface; what is missing is only the CAD-side generator, and that is
  scheduled: see BR-F22 and `Q-VI-4 ③`'s xsec loft, used when
  `solid_status != ok`.
- 🟢 **Duplicate-name divergence is resolved: 409 is correct (`Q-FD-1`).**
  `create_wing`'s 422 for the identical situation is the outlier and is being
  aligned to 409, not the reverse.
- 🟢 **`update_fuselage` is decided to preserve artefact pointers omitted from
  the payload (`Q-FD-7`).** Today it destructively replaces the row, so
  `step_path` / `solid_step_path` absent from an update are lost — the same
  defect class as issue #1094 (`ComponentEditDialog` hard-coding
  `model_ref: null`). The fix is a merge for these two fields specifically: a
  partial update must not destroy what it does not mention. Not yet
  implemented.
- 🟢 **Fidelity thresholds are decided (`Q-FD-4`).** `volume_ratio` /
  `area_ratio` ∈ `[0.95, 1.05]` is silent; `[0.85, 0.95) ∪ (1.05, 1.15]` emits
  `info`; `[0.70, 0.85) ∪ (1.15, 1.40]` emits `warning`; outside
  `[0.70, 1.40]`, or `volume_ratio ≤ 0.05`, or non-finite, the slice is
  **rejected**. A per-station `n` sitting at the `[0.5, 8.0]` bound emits
  `info`, escalating to `warning` above 25 % of stations. Medium-high
  confidence — the reject cuts are solid, the internal edges are engineering
  judgement (see `step-slicing/design.md` §F3 for the full band table and
  rationale). Not yet implemented.
- 🟢 **A 5–30 s slice joins the task model (`Q-FD-5`).** `POST /slice`'s
  contract changes from `200` with the body to `202 Accepted` with a task id,
  fetched from a status endpoint like every other long CAD operation in the
  system, plus a timeout. The single-user argument (ADR 0024) disposes of the
  throughput concern only — it does not supply progress, cancellation or a
  timeout, which is what is actually missing. Not yet implemented; see
  `step-slicing/design.md`.
- 🟢 **`number_of_slices` and `points_per_slice` are already bounded — the
  earlier "unbounded, no clamp found" claim was wrong (`Q-FD-6` bundle).**
  `number_of_slices` is `Form(ge=2, le=500)`; `points_per_slice` is
  `10 ≤ … ≤ 200` (`fuselage_slice.py:25-30`); the shell/adaptive station path
  additionally clamps at `min(…, 4096)` internally (`slicing.py:951`). These
  clamp the **station count**, not the sections that survive filtering — see
  the next item.
- 🟢 **≥ 2 usable slices are confirmed NOT guaranteed — a real defect
  (`Q-FD-6` bundle).** Three separate gates drop stations after cutting
  (`slicing.py:958-960, 987-993, 544-547`), and nothing between the loop and
  the return asserts `len(xsec_dicts) >= 2`; `slice_step_file` does not check
  either. A degenerate body returns HTTP 200 with 0 or 1 xsecs and fails only
  later, on the caller's `PUT`, against `min_length=2`. The CUSTOM OpenVSP
  handler already enforces exactly this invariant
  (`app/converters/openvsp_custom_handler.py:98-106`); this pipeline is
  missing the equivalent check.
- 🟢 **The `a`/`b` axis mapping gets a mechanism, not a bare assertion
  (`Q-FD-3`).** Collapse the two independent `2.0 * a` conversions
  (`cad_designer/aerosandbox/slicing.py:1291-1300`,
  `app/converters/openvsp_fuselage_handler.py:215`) into one
  `superellipse_to_asb_xsec(a, b, n)` seam so the half-axis convention holds
  by construction; at import time, check `2a ≤ 1.02·Y_extent(step)` and
  `2b ≤ 1.02·Z_extent(step)` per xsec, plus `max_x(2a)/max_x(2b)` within 20 %
  of `Y_extent/Z_extent` for the whole body, wherever a `step_path` survives;
  where there is no source, an aspect-ratio band `2a/2b ∈ [0.3, 3.0]` emits
  `severity="warning"`, never an exception. High confidence on the
  failure-mode analysis; medium on the specific 1.02 / 20 % / `[0.3, 3.0]`
  numbers. Not yet implemented.
