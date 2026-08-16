# step-slicing — Implementation Tasks

> Use-case task list, nested under module [`fuselage-design`](../tasks.md).
> Executable sequence to re-implement this slice from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker. Task ids are **slice-local** and map to the module
> list where noted.

## Prerequisites

- [ ] **SciPy** for `optimize.minimize` (`L-BFGS-B`) and `integrate.quad`.
- [ ] `app/core/exceptions.py` hierarchy plus the shared error envelope — this
      slice raises `InternalError` (500) and a validation error (422).
- [ ] `app/schemas/aeroplaneschema.py` — `FuselageSchema` and
      `FuselageXSecSuperEllipseSchema` define the output shape. See
      [`superellipse-xsecs/tasks.md`](../superellipse-xsecs/tasks.md) T-03/T-04.
- [ ] A writable temporary directory root.
- [ ] CadQuery / OCCT **optionally** present. Absent (e.g. `linux/aarch64`) the
      route must degrade to a clean 500 and the API must still start
      (ADR 0017).

No database is required for this slice — it persists nothing. 🟢

## Tasks

### Safety envelope

- [ ] **T-01 — `slice_step_file` signature and defaults.** (module T-14)

  ```python
  slice_step_file(file_content, filename,
                  number_of_slices=50, points_per_slice=30,
                  slice_axis="auto",
                  fuselage_name="Imported Fuselage") -> FuselageSliceResponse
  ```

  - Legacy origin: `app/services/fuselage_slice_service.py:28-116`
  - Definition of done: the defaults are reproduced exactly and a happy-path
    slice returns a `FuselageSchema` with ≥ 2 cross-sections.
  - Confidence: 🟢

- [ ] **T-02 — Lazy import of the geometry kernel.** (module T-15)
  Import `cad_designer.aerosandbox.slicing.slice_step_to_fuselage` **inside** the
  function; an `ImportError` becomes `InternalError` → 500.
  - Legacy origin: `fuselage_slice_service.py:42-48` (ADR 0017)
  - Definition of done: with the import patched to raise, `POST /slice` returns
    500 `internal_error` and every other route still works.
  - Confidence: 🟢

- [ ] **T-03 — Extension validation before any filesystem access.**
  (module T-16) Accept `.step` / `.stp` only.
  - Legacy origin: `fuselage_slice_service.py:28-116`
  - Definition of done: a `.stl` upload returns 422 and creates no temp file —
    assert the temp root is untouched, not merely that the response is 422.
  - Confidence: 🟢

- [ ] **T-04 — Path-traversal guard (S2083).** (module T-17)
  Reduce `filename` to its **basename**, build the temp path, and verify with
  `is_relative_to` before writing.
  - Legacy origin: `fuselage_slice_service.py:50-64`
  - Definition of done: an upload named `"../../etc/passwd.step"` writes to
    `<tmp>/passwd.step` and nothing outside the temp directory is touched.
  - Confidence: 🟢

- [ ] **T-05 — Guaranteed temp cleanup.** (module T-18)
  `rmtree` in a `finally` block regardless of outcome.
  - Legacy origin: `fuselage_slice_service.py` (slice flow)
  - Definition of done: with the slicer patched to raise mid-way, no temp
    directory remains.
  - Confidence: 🟢

- [ ] **T-06 — Persist nothing.**
  The route takes no aeroplane UUID and opens no session; the caller `PUT`s the
  returned `FuselageSchema` separately.
  - Legacy origin: `app/api/v2/endpoints/fuselage_slice.py:18`; absence of DB
    access in `fuselage_slice_service.py:28-116`
  - Definition of done: a successful slice writes no `fuselages` and no
    `fuselage_xsecs` row.
  - Confidence: 🟢

### Output integrity

- [ ] **T-07 — Non-finite sanitisation (GH#301).** (module T-19)
  Replace `NaN` / `Inf` with `None` before building the response.
  - Legacy origin: `fuselage_slice_service.py` (GH#301)
  - Definition of done: a degenerate slice produces `null` fields and the body
    round-trips through `json.dumps` / `json.loads`.
  - Confidence: 🟢

- [ ] **T-08 — Fidelity metrics, graded (`Q-FD-4`).** (module T-20)
  Compare the reconstructed superellipse loft against the original solid and
  report `volume_ratio` and `area_ratio`. Leave
  `original_tessellation_url` / `reconstructed_tessellation_url` as `None`.
  **Decided grading, not yet implemented** — see "Fidelity thresholds" in
  [`../requirements.md`](../requirements.md) for the full band table: silent
  `[0.95, 1.05]`, `info` `[0.85, 0.95) ∪ (1.05, 1.15]`, `warning`
  `[0.70, 0.85) ∪ (1.15, 1.40]`, reject outside `[0.70, 1.40]` or
  `volume_ratio ≤ 0.05` or non-finite; a bound-hitting `n` also warns.
  - Legacy origin: `fuselage_slice_service.py:113-115`
  - Definition of done: both ratios are present and finite on the happy path;
    the two URL fields are `null`; each band produces the matching
    `DesignWarning` severity and an out-of-band ratio rejects the slice.
  - Confidence: 🟢

### Superellipse mathematics

- [ ] **T-09 — Superellipse primitives.** (module T-11)

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

- [ ] **T-10 — `fit_symmetric_superellipse`.** (module T-12)
  Force `center = [0, mean(z)]`; shift, convert to `(θ, r)`, **mirror**
  (`θ → −θ`, same `r`); minimise
  `objective = mean((r_i − r_fit(θ_i))²) + 0.01 · (perimeter_fit − perimeter_actual)²`
  with `scipy.optimize.minimize`, method `L-BFGS-B`, `x0 = [1.0, 1.0, 2.0]`,
  bounds `a, b ∈ (1e-3, ∞)` and **`n ∈ [0.5, 8.0]`**.
  - Legacy origin: `slicing.py:610-661`
  - Definition of done: a circle of radius `r` fits `n ≈ 2`, `a ≈ b ≈ r`; a
    near-rectangular contour returns `n ≤ 8.0`; an asymmetric contour still
    returns a left/right-symmetric fit with its centre on the Z axis.
  - Confidence: 🟢

- [ ] **T-11 — Keep the asymmetric `fit_superellipse` out of the fuselage path.**
  (module T-13) It exists (l.663) but the fuselage pipeline uses the symmetric
  variant only.
  - Legacy origin: `slicing.py:663`
  - Definition of done: the fuselage slice flow has no call site for the
    asymmetric fit.
  - Confidence: 🟢

- [ ] **T-12 — Emit half-axes, matching the persistence contract, with a
  decided unit-detection mechanism (`Q-FD-2`).**
  The fitted `a` and `b` are Y and Z **half-axes**, so the response is
  directly `PUT`-able through
  [`superellipse-xsecs/`](../superellipse-xsecs/tasks.md) with no shape
  conversion. **Confirmed and now answered by the maintainer, 2026-08-13:**
  "in metres" holds only when the uploaded STEP is authored in metres — the
  slicer takes no unit parameter and the service performs no scaling (see
  `design.md` §F4), so a millimetre STEP is stored 1000× too large, silently,
  and this is the most reachable silent-1000× path in the system. The
  decided fix, shared with the `construction-parts` STEP importer (which
  assumes the opposite unit): read the STEP header's `SI_UNIT`, offer an
  explicit override pre-filled with the detected value (the project's own
  RV-7 fixture carries contradictory `SI_UNIT` declarations, so the header
  alone is not trustworthy), and add a plausibility check on absolute
  dimensions (RC fuselage 0.3–3 m) as the layer that catches a uniform scale
  error even when the header is silent. Not yet implemented — do **not**
  reproduce the silent assumption in a re-implementation.
  - Legacy origin: `app/schemas/aeroplaneschema.py:711-723` (gh-706);
    data-dictionary §Module: fuselage-design
  - Definition of done: a round-trip test slices a STEP, `PUT`s the result and
    reads it back with `a` and `b` unchanged — no factor of two, no scaling;
    a millimetre-authored fixture triggers the plausibility `DesignWarning`
    rather than silently storing a 1000×-oversized body.
  - Confidence: 🟢

### Slicing internals

- [ ] **T-13 — Adaptive station placement.** (module T-21)
  `adaptive_x_stations` distributes the requested slice count using the
  `_curvature_density` metric rather than uniformly.
  - Legacy origin: `slicing.py:347, 375`
  - Definition of done: a body with a sharp shoulder receives measurably more
    stations there than in the parallel mid-body, for the same total count.
  - Confidence: 🟢

- [ ] **T-14 — Outer-contour selection.** (module T-22)
  `select_outer_contour` keeps the cluster that **encloses the longitudinal
  axis** when a plane cuts several disjoint loops.
  - Legacy origin: `slicing.py:207-267`
  - Definition of done: a slice through a wheel well returns the outer skin, not
    the well.
  - Confidence: 🟢

- [ ] **T-15 — Arc-length point weighting.** (module T-23)
  Resample each contour by arc length so densely tessellated regions do not bias
  the fit. `points_per_slice` (default 30) sets the sample count.
  - Legacy origin: `slicing.py:116-152`
  - Definition of done: a contour with one heavily refined edge fits the same
    `(a, b, n)` as the uniformly tessellated equivalent, within tolerance.
  - Confidence: 🟢

- [ ] **T-16 — Solid vs shell cutting (gh-727).** (module T-24)
  Solids: `Workplane.split(keepTop=True)`. Shells: fall back to
  `BRepAlgoAPI_Section`.
  - Legacy origin: `slicing.py:476-489`
  - Definition of done: a shell STEP still yields contours; the fallback is
    exercised by a dedicated test fixture.
  - Confidence: 🟢

### REST layer

- [ ] **T-17 — The standalone `POST /slice` route, migrated to the task
  model (`Q-FD-5`).** (module T-26) Not nested under an aeroplane; returns a
  `FuselageSchema` the caller may then `PUT`. **Target status codes, not yet
  implemented:** `202 Accepted` with a task id plus a status endpoint
  returning `FuselageSliceResponse`, plus a timeout — replacing the legacy
  synchronous `200`. Full contract in [`../contracts.md`](../contracts.md).
  - Legacy origin: `app/api/v2/endpoints/fuselage_slice.py:18`
  - Definition of done: contract tests assert 202 with a pollable task id, the
    eventual result matching the legacy synchronous body, the 422 on a wrong
    extension and the 500 when the kernel is missing.
  - Confidence: 🟢 (decision); implementation not yet done

## Test Tasks

- [ ] **TT-01 — Happy path:** a valid solid `.step` yields a `FuselageSchema`
      with ≥ 2 cross-sections, finite `volume_ratio` and `area_ratio`, and no
      temp directory left behind.
- [ ] **TT-02 — Persists nothing:** after a successful slice, no `fuselages` and
      no `fuselage_xsecs` row exists.
- [ ] **TT-03 — Extension rejection:** `.stl` → 422, **and** the temp root is
      untouched.
- [ ] **TT-04 — Traversal guard:** `"../../etc/passwd.step"` writes only to the
      temp basename; nothing outside is opened.
- [ ] **TT-05 — Cleanup on failure:** the slicer raises, the response is 500 and
      no temp directory remains.
- [ ] **TT-06 — NaN sanitisation:** a degenerate slice produces `null`, and the
      body is valid JSON.
- [ ] **TT-07 — Fidelity metrics present** and finite on the happy path; the two
      tessellation URLs are `null`.
- [ ] **TT-08 — Missing kernel:** with the lazy import patched to raise,
      `POST /slice` returns 500 `internal_error` and other routes still serve.
- [ ] **TT-09 — Superellipse identities:** `n = 2` gives `area == π·a·b`;
      `perimeter` matches a reference ellipse approximation.
- [ ] **TT-10 — Fit accuracy:** a sampled circle of radius `r` yields `n ≈ 2`,
      `a ≈ b ≈ r`.
- [ ] **TT-11 — Fit bounds:** a near-rectangular contour returns `n ≤ 8.0`; a
      cross-like contour returns `n ≥ 0.5`.
- [ ] **TT-12 — Fit symmetry:** an asymmetric contour still yields a
      left/right-symmetric result with the centre on the Z axis.
- [ ] **TT-13 — Objective composition:** a hand-built case asserts
      `objective == radius_loss + 0.01 · length_loss`, so the weight cannot drift
      unnoticed.
- [ ] **TT-14 — Asymmetric fit unused:** the fuselage flow never calls
      `fit_superellipse`.
- [ ] **TT-15 — Shell fallback:** a shell STEP produces contours via
      `BRepAlgoAPI_Section`.
- [ ] **TT-16 — Outer-contour selection:** a multi-loop slice returns the outer
      skin.
- [ ] **TT-17 — Adaptive stations:** curvature-weighted placement beats uniform
      placement on a reference body's `volume_ratio`.
- [ ] **TT-18 — Tessellation independence:** two contours of the same shape, one
      heavily refined, fit the same `(a, b, n)` within tolerance.
- [ ] **TT-19 — Round trip:** slice a STEP, `PUT` the result, read it back — `a`
      and `b` are unchanged, in metres, as half-axes.

> Tests TT-01, TT-05, TT-07 and TT-15…TT-18 need a real geometry kernel and
> belong on the CI **slow** tier. TT-03, TT-04, TT-06, TT-08 and TT-09…TT-14 run
> without CadQuery and belong on the **fast** tier. 🟡 INFERRED from the tiering
> convention (ADR 0015), not from an existing test file.

## Data Migration Tasks

None. This slice owns no persistent state. 🟢

Fuselages **produced** by earlier runs of this pipeline are covered by
[`superellipse-xsecs/tasks.md`](../superellipse-xsecs/tasks.md) TM-01
(half-axis verification), which is the relevant audit if the axis convention was
ever misapplied here.

## Suggested Order

1. **T-01 → T-06** first — the safety envelope. Landing the lazy import, the
   extension check, the traversal guard and the `finally` cleanup **before** the
   pipeline internals means every later test runs inside a guaranteed-clean temp
   directory, and a half-finished slicer cannot leak state. T-02 blocks nothing
   but must be verified *without* CadQuery installed.
2. **T-09 → T-12** next — the superellipse mathematics. Pure functions, no
   geometry kernel, fully testable on the CI **fast** tier. **T-09 blocks T-10**
   (the objective needs `perimeter`). T-12 pins the unit contract shared with
   [`superellipse-xsecs/`](../superellipse-xsecs/tasks.md).
3. **T-07 → T-08** — output integrity. T-08 depends on T-09/T-10 existing (the
   reconstructed loft is built from fitted parameters); T-07 is independent and
   can land with step 1.
4. **T-13 → T-16** — the slicing internals, which need a real geometry kernel and
   therefore belong on the CI **slow** tier. T-14 and T-15 both feed T-10, so
   they should land before the fit is tuned against real bodies. T-16 is the
   gh-727 edge case and can trail the others.
5. **T-17** last — the route is thin and only wires what is already tested.

## Decided, Not Yet Implemented

Every question below was put to the maintainer, or resolved by direct code
lookup, during the 2026-08-13 → 2026-08-15 specification validation
interview. Nothing remains 🔴 in this slice.

- **Fidelity bands are decided** (`Q-FD-4`): silent / `info` / `warning` /
  reject on `volume_ratio` and `area_ratio` — see "Fidelity thresholds" in
  [`../requirements.md`](../requirements.md). → feeds T-08.
- **A bound-hitting exponent is decided to warn** (`Q-FD-4`): `info` per
  station, `warning` above 25 % of stations. → feeds T-08, T-10.
- **`number_of_slices` / `points_per_slice` are already clamped — resolved by
  code lookup, not a gap** (`Q-FD-6` bundle): `Form(ge=2, le=500)` and
  `10 ≤ … ≤ 200` at the HTTP boundary, plus an internal `min(…, 4096)` on the
  shell path.
- **A 5–30 s slice is decided to join the task model** (`Q-FD-5`): `202` plus
  a status endpoint plus a timeout. → feeds T-17.
- **`slice_axis="auto"` is confirmed — resolved by code lookup**
  (`Q-FD-6` bundle): `detect_longest_axis`, a pure bounding-box comparison;
  alternatives are `"x"` / `"y"` / `"z"`, anything else 422s at the endpoint.
- **≥ 2 usable slices are confirmed NOT guaranteed — a real defect, resolved
  by code lookup** (`Q-FD-6` bundle): three station-dropping gates exist with
  no final assertion; a degenerate body returns 200 with 0 or 1 xsecs today.
  → feeds T-01.
- **The second STEP ingestion path is confirmed dead, not merely apparent**
  (`Q-FD-8`, `P-DEAD-0` rule 3). `FuselageConfiguration.from_step_file`
  (`FuselageConfiguration.py:114-140`) has never executed — the
  `TypeError`-raising `analysis_specific_options = {dict(...)}` line proves
  it. Its removal is recorded in `../requirements.md`, not executed (ADR 0002
  freeze). This slice owns the module's one working STEP ingestion route.
- **What unit an uploaded STEP is assumed to be in is decided (`Q-FD-2`)**:
  header detection + explicit override + a plausibility check, unified with
  the `construction-parts` importer's opposite assumption. → feeds T-12.
