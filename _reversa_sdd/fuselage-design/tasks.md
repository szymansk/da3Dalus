# fuselage-design — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists: [`superellipse-xsecs/tasks.md`](superellipse-xsecs/tasks.md),
> [`step-slicing/tasks.md`](step-slicing/tasks.md).

## Prerequisites

- [ ] `aeroplane-core` available — every route resolves an aeroplane by UUID,
      and `fuselages` cascade-delete with the aeroplane.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009). The module never commits.
- [ ] `app/core/exceptions.py` hierarchy plus `_raise_http_from_domain`
      (`aeroplane/base.py:52-67`) — note this module uses `ConflictError`.
- [ ] `component_tree_service` reachable for the `fuselage:<name>` group
      auto-sync (gh#108), imported lazily to break the cycle.
- [ ] `ARTIFACTS_BASE_DIR` configured and `.resolve()`d
      (`app/core/config.py:24-32`) — the STEP download routes read relative
      paths against it.
- [ ] **SciPy** for `optimize.minimize` (`L-BFGS-B`) and `integrate.quad`.
- [ ] CadQuery / OCCT **optionally** present. Absent (e.g. `linux/aarch64`) the
      module must still serve CRUD; only `POST /slice` degrades to a clean 500
      (ADR 0017).

## Tasks

### Persistence

- [ ] **T-01 — `fuselages` table and `FuselageModel`.**
  Columns: `name` (required), `symmetric` (Boolean, **default `False`**),
  `step_path` (nullable String, relative), `solid_step_path` (nullable String,
  relative), `aeroplane_id` FK → `aeroplanes.id` `ON DELETE CASCADE`.
  - Legacy origin: `app/models/aeroplanemodel.py:526`; `symmetric` rationale at
    `:529-533` (gh-715)
  - Definition of done: a fuselage created without `symmetric` reads back
    `false`, and deleting the aeroplane removes the row.
  - Confidence: 🟢

- [ ] **T-02 — `fuselage_xsecs` table and `FuselageXSecSuperEllipseModel`.**
  Columns: `xyz` (JSON `[x,y,z]`, **metres**), `a` (Float, Y half-axis, m),
  `b` (Float, Z half-axis, m), `n` (Float, exponent), `sort_index` (Integer,
  default 0), `fuselage_id` FK `ON DELETE CASCADE`. Ordered by `sort_index`,
  `cascade="all, delete-orphan"`.
  - Legacy origin: `app/models/aeroplanemodel.py:512`
  - Definition of done: deleting a fuselage removes every cross-section; reads
    come back in `sort_index` order.
  - Confidence: 🟢

- [ ] **T-03 — `FuselageSchema` with `min_length=2`.**
  `name`, `x_secs` (**`min_length=2`**), `symmetric: bool = False`,
  `step_path: str | None = None`, `solid_step_path: str | None = None`.
  - Legacy origin: `app/schemas/aeroplaneschema.py:755`
  - Definition of done: a payload with one cross-section is rejected at
    validation time (→ 422).
  - Confidence: 🟢

- [ ] **T-04 — `FuselageXSecSuperEllipseSchema` and the axis convention.**
  `xyz`, `a`, `b`, `n` all required; `a` is the **Y half-axis** mapping to ASB
  `FuselageXSec.width`, `b` the **Z half-axis** mapping to `.height`. Document
  it on the fields — they are **half-axes, not diameters**.
  - Legacy origin: `app/schemas/aeroplaneschema.py:711-723` (gh-706)
  - Definition of done: a conversion test asserts `width == a` and
    `height == b` on the produced ASB `FuselageXSec`.
  - Confidence: 🟢

### Lifecycle

- [ ] **T-05 — `create_fuselage` with a 409 on duplicates.**
  Persist the fuselage and its ordered cross-sections; a name already present on
  the aeroplane raises `ConflictError` → **409**.
  - Legacy origin: `app/services/fuselage_service.py:63, 80-84`
  - Definition of done: a second create with the same name returns 409
    `conflict`. (409 is the confirmed, correct contract — `Q-FD-1`; `create_wing`
    is being aligned to it, not the reverse, so no divergence survives to
    document.)
  - Confidence: 🟢

- [ ] **T-06 — `update_fuselage` merges artefact pointers instead of
  destructively replacing.** **Target behaviour, decided by `Q-FD-7` — the
  legacy code replaces the row wholesale (`fuselage_service.py:120-122`); the
  re-implementation must not.** Build the replacement row from the payload as
  before, but when `step_path` / `solid_step_path` are absent from the
  payload, carry over the previous row's values rather than nulling them —
  the same principle as issue #1094 (`ComponentEditDialog` erasing
  `model_ref` on every edit): a partial update must not destroy what it does
  not mention.
  - Legacy origin: `fuselage_service.py:103, 120-122` (current, superseded
    behaviour)
  - Definition of done: a `POST` that omits `step_path` from the payload
    leaves the stored `step_path` unchanged; a `POST` that explicitly sets it
    to `null` does clear it.
  - Confidence: 🟢 (decision); implementation not yet done

- [ ] **T-07 — `get_fuselage`, `list_fuselage_names`, `delete_fuselage`.**
  Lookup by name under an aeroplane, `NotFoundError` → 404 on a miss; delete
  cascades to the cross-sections.
  - Legacy origin: `fuselage_service.py:45, 137, 160`
  - Definition of done: unknown fuselage name → 404 with the `not_found`
    envelope; delete leaves no `fuselage_xsecs` rows behind.
  - Confidence: 🟢

- [ ] **T-08 — Cross-section CRUD by index.**
  `get_fuselage_cross_sections`, `delete_all_cross_sections`,
  `get_cross_section`, `create_cross_section`, `update_cross_section`,
  `delete_cross_section`.
  - Legacy origin: `fuselage_service.py:193, 219, 244, 276, 327, 364`
  - Definition of done: `DELETE .../cross_sections` empties the stack but keeps
    the fuselage row; an out-of-range index returns 404.
  - Confidence: 🟢 (the exact out-of-range behaviour is 🟡)

- [ ] **T-09 — Component-tree group auto-sync (gh#108).**
  Create/update drive `sync_group_for_fuselage`; delete calls
  `delete_synced_nodes("fuselage:<name>")`, imported lazily.
  - Legacy origin: `fuselage_service.delete_fuselage:179-181`
  - Definition of done: a group node with `synced_from = "fuselage:<name>"`
    appears on create and disappears on delete.
  - Confidence: 🟢

- [ ] **T-10 — STEP artefact download routes.**
  `GET .../fuselages/{name}/step` and `.../solid_step` resolve the stored
  **relative** path against `settings.ARTIFACTS_BASE_DIR` and stream the file;
  a `NULL` column yields 404.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/fuselages.py:198, 234`;
    `app/core/config.py:24-32`
  - Definition of done: a fuselage without `solid_step_path` returns 404 on
    `/solid_step`; the resolved path never escapes `ARTIFACTS_BASE_DIR`.
  - Confidence: 🟢 (the 404-on-null mapping is 🟡)

### Superellipse mathematics

- [ ] **T-11 — Superellipse primitives.**

  ```
  r(θ)        = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)
  perimeter   = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ        (scipy quad, limit = 200)
  area        = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)
  polygon_area = shoelace formula over the sliced outline
  ```

  - Legacy origin: `cad_designer/aerosandbox/slicing.py:585-608`
  - Definition of done: for `n = 2`, `area` reproduces `π·a·b` and `perimeter`
    matches Ramanujan's ellipse approximation within tolerance.
  - Confidence: 🟢

- [ ] **T-12 — `fit_symmetric_superellipse`.**
  Force `center = [0, mean(z)]`; shift, convert to `(θ, r)`, **mirror**
  (`θ → −θ`, same `r`); minimise
  `objective = mean((r_i − r_fit(θ_i))²) + 0.01 · (perimeter_fit − perimeter_actual)²`
  with `scipy.optimize.minimize`, method `L-BFGS-B`, `x0 = [1.0, 1.0, 2.0]`,
  bounds `a, b ∈ (1e-3, ∞)` and **`n ∈ [0.5, 8.0]`**.
  - Legacy origin: `slicing.py:610-661`
  - Definition of done: a circle of radius `r` fits `n ≈ 2`, `a ≈ b ≈ r`; a
    near-rectangular contour returns `n ≤ 8.0`; an asymmetric contour still
    returns a left/right-symmetric fit.
  - Confidence: 🟢

- [ ] **T-13 — Keep the asymmetric `fit_superellipse` out of the fuselage path.**
  It exists (l.663) but the fuselage pipeline uses the symmetric variant only.
  - Legacy origin: `slicing.py:663`
  - Definition of done: the fuselage slice flow has no call site for the
    asymmetric fit.
  - Confidence: 🟢

### Slicing pipeline

- [ ] **T-14 — `slice_step_file` signature and flow.**

  ```python
  slice_step_file(file_content, filename,
                  number_of_slices=50, points_per_slice=30,
                  slice_axis="auto",
                  fuselage_name="Imported Fuselage") -> FuselageSliceResponse
  ```

  - Legacy origin: `app/services/fuselage_slice_service.py:28-116`
  - Definition of done: the defaults are reproduced exactly and a happy-path
    slice returns a `FuselageSchema` with ≥ 2 cross-sections. **Decided target
    contract (`Q-FD-5`, not yet implemented): the endpoint returns `202` with
    a task id rather than `200` with the body — see
    [`step-slicing/tasks.md`](step-slicing/tasks.md) for the full task-model
    breakdown.** Also confirmed defect (`Q-FD-6` bundle): the pipeline does
    **not** guarantee ≥ 2 *usable* slices survive station filtering before
    returning — assert it explicitly rather than relying on the caller's
    `PUT` to fail later.
  - Confidence: 🟢

- [ ] **T-15 — Lazy import of the geometry kernel.**
  Import `cad_designer.aerosandbox.slicing.slice_step_to_fuselage` **inside** the
  function; an `ImportError` becomes `InternalError` → 500.
  - Legacy origin: `fuselage_slice_service.py:42-48` (ADR 0017)
  - Definition of done: with the import patched to raise, `POST /slice` returns
    500 `internal_error` and every other route still works.
  - Confidence: 🟢

- [ ] **T-16 — Extension validation before any filesystem access.**
  Accept `.step` / `.stp` only.
  - Legacy origin: `fuselage_slice_service.py:28-116`
  - Definition of done: a `.stl` upload returns 422 and creates no temp file
    (assert the temp root is untouched).
  - Confidence: 🟢

- [ ] **T-17 — Path-traversal guard (S2083).**
  Reduce `filename` to its **basename**, build the temp path, and verify with
  `is_relative_to` before writing.
  - Legacy origin: `fuselage_slice_service.py:50-64`
  - Definition of done: an upload named `"../../etc/passwd.step"` writes to
    `<tmp>/passwd.step` and nothing outside the temp directory is touched.
  - Confidence: 🟢

- [ ] **T-18 — Guaranteed temp cleanup.**
  `rmtree` in a `finally` block regardless of outcome.
  - Legacy origin: `fuselage_slice_service.py` (slice flow)
  - Definition of done: with the slicer patched to raise mid-way, no temp
    directory remains.
  - Confidence: 🟢

- [ ] **T-19 — Non-finite sanitisation (GH#301).**
  Replace `NaN` / `Inf` with `None` before building the response.
  - Legacy origin: `fuselage_slice_service.py` (GH#301)
  - Definition of done: a degenerate slice produces `null` fields and the body
    round-trips through `json.dumps`/`json.loads`.
  - Confidence: 🟢

- [ ] **T-20 — Fidelity metrics, graded (`Q-FD-4`).**
  Compare the reconstructed superellipse loft against the original solid and
  report `volume_ratio` and `area_ratio`. Leave
  `original_tessellation_url` / `reconstructed_tessellation_url` as `None`.
  **Decided grading, not yet implemented:** `[0.95, 1.05]` silent;
  `[0.85, 0.95) ∪ (1.05, 1.15]` → `DesignWarning` `severity="info"`;
  `[0.70, 0.85) ∪ (1.15, 1.40]` → `severity="warning"`; outside
  `[0.70, 1.40]`, or `volume_ratio ≤ 0.05`, or non-finite → **reject the
  slice**. A per-station `n` at the `[0.5, 8.0]` bound emits `info`,
  escalating to `warning` above 25 % of stations.
  - Legacy origin: `fuselage_slice_service.py:113-115`
  - Definition of done: both ratios are present and finite on the happy path;
    the two URL fields are `null`; a ratio in each band produces the matching
    `DesignWarning` severity, and a ratio outside `[0.70, 1.40]` returns an
    error response instead of a `FuselageSliceResponse`.
  - Confidence: 🟢

- [ ] **T-21 — Adaptive station placement.**
  `adaptive_x_stations` distributes the requested slice count using the
  `_curvature_density` metric rather than uniformly.
  - Legacy origin: `slicing.py:347, 375`
  - Definition of done: a body with a sharp shoulder receives measurably more
    stations there than in the parallel mid-body, for the same total count.
  - Confidence: 🟢

- [ ] **T-22 — Outer-contour selection.**
  `select_outer_contour` keeps the cluster that **encloses the longitudinal
  axis** when a plane cuts several disjoint loops.
  - Legacy origin: `slicing.py:207-267`
  - Definition of done: a slice through a wheel well returns the outer skin, not
    the well.
  - Confidence: 🟢

- [ ] **T-23 — Arc-length point weighting.**
  Resample each contour by arc length so densely tessellated regions do not bias
  the fit.
  - Legacy origin: `slicing.py:116-152`
  - Definition of done: a contour with one heavily refined edge fits the same
    `(a, b, n)` as the uniformly tessellated equivalent, within tolerance.
  - Confidence: 🟢

- [ ] **T-24 — Solid vs shell cutting (gh-727).**
  Solids: `Workplane.split(keepTop=True)`. Shells: fall back to
  `BRepAlgoAPI_Section`.
  - Legacy origin: `slicing.py:476-489`
  - Definition of done: a shell STEP still yields contours; the fallback is
    exercised by a dedicated test fixture.
  - Confidence: 🟢

### REST layer

- [ ] **T-25 — Fuselage and cross-section routes.**
  Exactly as listed in [`contracts.md`](contracts.md), with the shared
  domain→HTTP mapping — including the **409** on duplicate create.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/fuselages.py`
  - Definition of done: contract tests assert every status code, notably the
    409 (not 422) on a duplicate name.
  - Confidence: 🟢

- [ ] **T-26 — The standalone `POST /slice` route, migrated to the task
  model.** Not nested under an aeroplane and persisting nothing — it returns a
  `FuselageSchema` the caller may then `PUT`. **Target contract (`Q-FD-5`, not
  yet implemented): `202 Accepted` with a task id plus a status endpoint
  returning `FuselageSliceResponse`, with a timeout, rather than the legacy
  synchronous `200`.**
  - Legacy origin: `app/api/v2/endpoints/fuselage_slice.py:18`
  - Definition of done: a successful slice writes no database row; the route
    returns 202 with a pollable task id and the eventual result matches the
    legacy synchronous body.
  - Confidence: 🟢 (decision); implementation not yet done

- [ ] **T-27 — Geometry-change fan-out.**
  Route fuselage mutations through `invalidation_service.mark_ops_dirty` so
  dependent operating points become `DIRTY`.
  - Legacy origin: `app/services/invalidation_service.py:16-93`
  - Definition of done: creating or deleting a fuselage marks the aircraft's
    non-`DIRTY`/`COMPUTING` operating points `DIRTY`.
  - Confidence: 🟡 INFERRED — the cross-module note states the requirement for
    "any new geometry-mutating path"; the fuselage-side call sites were not
    enumerated.

## Test Tasks

- [ ] **TT-01 — Happy path:** create a fuselage with three cross-sections, read
      it back in `sort_index` order, delete it and assert the cascade.
- [ ] **TT-02 — Failure:** a one-cross-section payload returns 422.
- [ ] **TT-03 — Duplicate name returns 409** — the confirmed contract
      (`Q-FD-1`); `create_wing` now matches, so no divergence to note.
- [ ] **TT-04 — `symmetric` default is `false`** on a fuselage created without
      the field, in contrast to a wing's `true`.
- [ ] **TT-05 — Update preserves artefact pointers:** a `POST` without
      `step_path` in the payload leaves the stored `step_path` unchanged
      (`Q-FD-7`, target behaviour — supersedes the legacy destructive-replace
      test).
- [ ] **TT-06 — Component-tree sync:** `fuselage:<name>` node appears on create
      and is removed on delete.
- [ ] **TT-07 — STEP download:** a fuselage without `solid_step_path` returns
      404; a present path resolves under `ARTIFACTS_BASE_DIR`.
- [ ] **TT-08 — Superellipse identities:** `n = 2` gives `area == π·a·b`;
      `perimeter` matches a reference ellipse approximation.
- [ ] **TT-09 — Fit accuracy:** a sampled circle yields `n ≈ 2`, `a ≈ b ≈ r`.
- [ ] **TT-10 — Fit bounds:** a near-rectangular contour returns `n ≤ 8.0`; a
      cross-like contour returns `n ≥ 0.5`.
- [ ] **TT-11 — Fit symmetry:** an asymmetric contour still yields a
      left/right-symmetric result with the centre on the Z axis.
- [ ] **TT-12 — Extension rejection:** `.stl` → 422, no temp file created.
- [ ] **TT-13 — Traversal guard:** `"../../etc/passwd.step"` writes only to the
      temp basename.
- [ ] **TT-14 — Cleanup on failure:** the slicer raises, no temp directory
      remains.
- [ ] **TT-15 — NaN sanitisation:** a degenerate slice produces `null`, and the
      body is valid JSON.
- [ ] **TT-16 — Fidelity metrics present** and finite on the happy path.
- [ ] **TT-17 — Missing kernel:** with the lazy import patched to raise,
      `POST /slice` returns 500 and other routes still serve.
- [ ] **TT-18 — Shell fallback:** a shell STEP produces contours via
      `BRepAlgoAPI_Section`.
- [ ] **TT-19 — Outer-contour selection:** a multi-loop slice returns the outer
      skin.
- [ ] **TT-20 — Adaptive stations:** curvature-weighted placement beats uniform
      placement on a reference body's `volume_ratio`.
- [ ] **TT-21 — ASB axis mapping:** `width == a` and `height == b` on the
      converted `FuselageXSec`.

## Data Migration Tasks

- [ ] **TM-01 — Verify the half-axis interpretation of existing rows.** If any
      historical importer wrote full widths instead of half-axes, those
      fuselages are twice their intended size. Compare `2·a` against the source
      STEP bounding box where a `step_path` exists. **This audit query is the
      same check as `Q-FD-3`'s import-time plausibility check — run it once
      over rows that still have a `step_path`; a row whose `2a` exceeds the
      STEP Y-extent by ≈ 2× is a pre-fix full-width row. Rows with no
      surviving `step_path` cannot be checked and must be reported as
      `unverified`, not assumed clean.** 🟡 mechanism decided (`Q-FD-3`), audit
      itself still to run against the real database.
- [ ] **TM-02 — Backfill `solid_step_path` for VSP-imported fuselages** that
      predate gh-731, by re-running `openvsp_solid_sewing_service` over the
      existing `step_path`. 🟡
- [ ] **TM-03 — Audit `symmetric` on imported sub-fuselages.** Rows imported
      before gh-715 default to `False`, so paired gear struts and fairings would
      render on one side only. 🟡

## Suggested Order

1. **T-01 → T-04** first — the two tables and the two schemas. T-04's axis
   convention must be settled before any converter or fit code is written; a
   swapped `a`/`b` is silent and rotates the whole body.
2. **T-05 → T-10** next — the lifecycle and the REST-visible semantics. T-06 is
   **decided to change** (`Q-FD-7`): implement the merge/preserve behaviour
   directly rather than the legacy destructive replace — the gap that used to
   block this is closed. T-09 depends on `aeroplane-core`'s component tree
   existing.
3. **T-11 → T-13** — the superellipse mathematics, independent of everything
   else and fully unit-testable without a geometry kernel. T-11 blocks T-12
   (the objective needs `perimeter`).
4. **T-14 → T-20** — the slice service. T-15 → T-18 are the safety envelope and
   should land before the pipeline internals, so every later test runs inside a
   guaranteed-clean temp directory. T-20 blocks nothing but is what makes the
   result reviewable.
5. **T-21 → T-24** — the slicing internals, which need a real geometry kernel
   and therefore belong on the CI **slow** tier. T-24 is the gh-727 edge case
   and can trail the others.
6. **T-25 → T-27** last — the REST layer is thin. T-27 needs
   `invalidation_service` to exist.

## Decided, Not Yet Implemented

Every question that used to sit in this module's gap register was put to the
maintainer during the 2026-08-13 → 2026-08-15 specification validation
interview and answered. Nothing remains 🔴 in this module. What follows is
**decided direction awaiting implementation**, not open design questions —
each item names the task above it feeds.

- **`FuselageConfiguration.from_step_file` is confirmed dead** (`Q-FD-8`,
  `P-DEAD-0` rule 3) — its removal is recorded in `requirements.md`, not
  executed, because `FuselageConfiguration.py` sits inside the ADR 0002
  freeze. The premise that the xsec path is "the only parametric fuselage
  description because nothing else can build one" is corrected by `Q-FD-8b`:
  the xsecs are a first-class authoring surface regardless. → feeds T-14 note.
- **Duplicate-name status is resolved: 409 is correct** (`Q-FD-1`).
  `create_wing` is being aligned to it — no divergence survives to reconcile.
  → T-05, T-25.
- **`update_fuselage` is decided to merge, not replace** (`Q-FD-7`): a
  partial payload must preserve `step_path` / `solid_step_path` when they are
  omitted. → T-06.
- **Fidelity bands are decided** (`Q-FD-4`): silent / `info` / `warning` /
  reject thresholds on `volume_ratio` and `area_ratio`, plus a graded warning
  on a bound-hitting `n`. → T-20.
- **`number_of_slices` / `points_per_slice` are already clamped — this was a
  documentation gap, not a code gap** (`Q-FD-6` bundle): `Form(ge=2, le=500)`
  and `10 ≤ … ≤ 200` at the HTTP boundary, plus an internal `min(…, 4096)` on
  the shell path. → T-14.
- **A 5–30 s slice joins the task model** (`Q-FD-5`): `202 Accepted` plus a
  status endpoint and a timeout, replacing the synchronous `200`. → T-14,
  T-26.
- **The `a`/`b` ↔ `width`/`height` mapping gets a decided mechanism**
  (`Q-FD-3`): one conversion seam plus import-time and no-source plausibility
  checks, not a bare assertion. → T-04, TM-01.
