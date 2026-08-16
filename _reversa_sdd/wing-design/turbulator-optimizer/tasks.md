# turbulator-optimizer — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md). ADR 0012.

## Prerequisites

- [ ] `wing_xsec_details` 1:1 side table available (use case
      [`cross-section-crud`](../cross-section-crud/tasks.md) T-03) — the
      turbulator hangs off it.
- [ ] `_assert_non_terminal_xsec_or_raise` in place
      ([`cross-section-crud`](../cross-section-crud/tasks.md) T-08) — the
      turbulator is segment-scoped.
- [ ] `section_aoa_service` available, supplying **half-span** sections with
      their operating `(CL, Re)` and reference areas `S_i` (module
      `aero-analysis`).
- [ ] NeuralFoil (via AeroSandbox) available for `cd(CL, Re, xtr_upper)` and
      `analysis_confidence`. It is an **optional heavy dependency** — probe at
      import (ADR 0017).
- [ ] The gh-934 topology extension: `WingSegment` and `WingConfiguration`
      accept a `turbulator` parameter. This is the **one approved exception** to
      the frozen-topology rule (ADR 0002).
- [ ] `get_db()` owning the transaction (ADR 0009).

## Tasks

- [ ] **T-01 — `wing_xsec_turbulators` table and model.**
  `wing_xsec_detail_id` FK → `wing_xsec_details.id` `ON DELETE CASCADE` and
  **unique** (1:1); `form` (String, nullable), `height_mm` (Float, nullable,
  **mm**), `position_root` (Float, nullable, x/c), `position_tip` (Float,
  nullable, x/c), `enabled` (Boolean, **`NOT NULL`**, default `True`).
  - Legacy origin: `app/models/aeroplanemodel.py:83` (gh-934)
  - Definition of done: a second turbulator for the same `wing_xsec_detail_id`
    raises an `IntegrityError`; deleting the station cascades the turbulator
    away.
  - Confidence: 🟢

- [ ] **T-02 — `TurbulatorDetailSchema`.**
  `form ∈ {zigzag, dots, thread}` default **`zigzag`**; `height_mm` default
  **`0.3`** with constraint **`≥ 0`**; `position_root` **required**,
  `∈ [0, 1]`; `position_tip` optional, `∈ [0, 1]`, **falling back to
  `position_root`**; `enabled` default **`True`**.
  - Legacy origin: `app/schemas/aeroplaneschema.py:233`
  - Definition of done: an omitted `form`/`height_mm` yields `zigzag`/`0.3`; a
    missing `position_root` → 422; `position_root = 1.2` → 422;
    `height_mm = -0.1` → 422; `height_mm = 0` → 200; an omitted `position_tip`
    resolves to `position_root`.
  - Confidence: 🟢

- [ ] **T-03 — Turbulator CRUD routes with the terminal guard.**
  `GET` / `PUT` / `DELETE` on
  `/aeroplanes/{id}/wings/{wing_name}/cross_sections/{i}/turbulator`, calling
  `_assert_non_terminal_xsec_or_raise` on every write.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` turbulator routes;
    `app/services/wing_service.py:151-156`
  - Definition of done: `PUT` with `position_root = 0.35` on index 0 → 200; the
    same write on the terminal index → 422 `validation_error`.
  - Confidence: 🟢

- [ ] **T-04 — `enabled` as a toggle, not a delete.**
  Setting `enabled = false` retains the row; the CAD build omits the trip strip.
  - Legacy origin: `app/models/aeroplanemodel.py:83`
  - Definition of done: after `enabled = false` the row still reads back with
    its configured positions, and the CAD build excludes the strip.
  - Confidence: 🟢

- [ ] **T-05 — Optimiser constants.**

  ```
  XTR_GRID              = linspace(0.2, 0.9, 15)     # x/c sweep
  _ALPHA_GRID           = linspace(-4.0, 14.0, 37)   # cd-at-CL lookup
  _CONFIDENCE_THRESHOLD = 0.80                       # warning gate
  ```

  - Legacy origin: `app/services/turbulator_optimizer_service.py:53, 56, 60`
  - Definition of done: `XTR_GRID` has exactly 15 values spanning `[0.2, 0.9]`
    inclusive; `_ALPHA_GRID` has exactly 37 values spanning `[-4.0, 14.0]`.
  - Confidence: 🟢

- [ ] **T-06 — Natural-transition baseline.**

  ```
  cd_clean = cd(CL, Re, xtr_upper = 1.0)
  ```

  `xtr_upper = 1.0` means "no forced transition". This is the reference every
  tripped result is measured against — **not** the first grid point.
  - Legacy origin: `app/services/turbulator_optimizer_service.py` (`cd_clean`)
  - Definition of done: a test asserts the baseline call uses `xtr_upper = 1.0`
    and that it is *not* `XTR_GRID[0]`.
  - Confidence: 🟢

- [ ] **T-07 — Sweep and finite-only argmin.**

  ```
  i_opt    = argmin over FINITE cd values
  xtr_opt  = XTR_GRID[i_opt]
  delta_cd = cd_tripped − cd_clean          # negative = improvement
  ```

  - Legacy origin: `app/services/turbulator_optimizer_service.py`
  - Definition of done: a sweep with NaNs at indices 0, 3 and 14 still returns a
    finite `xtr_opt` drawn from the remaining values; `xtr_opt` is always a
    member of `XTR_GRID`.
  - Confidence: 🟢

- [ ] **T-08 — Warning: no optimum (all-NaN sweep).**
  Emit a warning and **no `xtr_opt`**; substitute nothing.
  - Legacy origin: `app/services/turbulator_optimizer_service.py:223-268`
    (ADR 0012)
  - Definition of done: an all-NaN section reports a warning, omits `xtr_opt`,
    and a test asserts **no** fallback value (such as `0.2` or the midpoint)
    appears anywhere in the result.
  - Confidence: 🟢

- [ ] **T-09 — Warning: low analysis confidence.**
  When the **mean** `analysis_confidence` for the section is below
  `_CONFIDENCE_THRESHOLD = 0.80`, return the result **and** a confidence
  warning. It is a trust signal, not a rejection.
  - Legacy origin: `app/services/turbulator_optimizer_service.py:223-268`,
    `:294-331`
  - Definition of done: mean confidence `0.7` → result present **plus** warning;
    mean confidence `0.85` → result present, no warning. A test pins that the
    gate uses the **mean**, not the minimum.
  - Confidence: 🟢

- [ ] **T-10 — Warning: boundary optimum.**
  When `i_opt ∈ {0, len−1}`, report the boundary value **and** warn that the
  true minimum may lie outside `[0.2, 0.9]`. **Do not widen the grid.**
  - Legacy origin: `app/services/turbulator_optimizer_service.py:294-331`
  - Definition of done: an optimum at index 0 and one at index 14 both produce
    the warning and still report their value; a test asserts `XTR_GRID` is
    unchanged (no auto-extension).
  - Confidence: 🟢

- [ ] **T-11 — Aircraft-level `ΔCD0` roll-up.**

  ```
  ΔCD0 = symmetry_factor · Σ (Δcd_i · S_i) / S_ref
  symmetry_factor = 2 for a symmetric wing
                    (section_aoa_service returns half-span sections only)
  ```

  - Legacy origin: `app/services/turbulator_optimizer_service.py`
  - Definition of done: for a symmetric wing with known `Δcd_i`, `S_i` and
    `S_ref`, `ΔCD0` equals twice the area-weighted sum. A companion test asserts
    the factor is applied **once** — the most likely defect here is a double
    application that is invisible in the output.
  - Confidence: 🟢

- [ ] **T-12 — `POST /aeroplanes/{id}/turbulator/optimize` route.**
  Aircraft-scoped: resolve the aeroplane, pull half-span sections from
  `section_aoa_service`, run T-06…T-10 per section, roll up per T-11, and return
  per-section `xtr_opt` / `delta_cd` plus all warnings.
  - Legacy origin:
    `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:173`
  - Definition of done: a seeded aircraft returns 200 with one entry per
    half-span section and an aircraft-level `ΔCD0`; an unknown aeroplane → 404.
  - Confidence: 🟢

- [ ] **T-13 — Defensive import of the surrogate.**
  Probe AeroSandbox / NeuralFoil at import (ADR 0017) so an `linux/aarch64` host
  without it can still serve turbulator CRUD.
  - Legacy origin: cross-module platform note in `code-analysis.md`; ADR 0017
  - Definition of done: with the surrogate unimportable, T-03's CRUD routes
    still return 200. 🔴 What `POST /turbulator/optimize` should return in that
    state is unresolved — see Pending Gaps; pin whatever the legacy does and
    record it.
  - Confidence: 🟡

- [ ] **T-14 — Topology `Turbulator` and its wiring.**
  `Turbulator(position_root, form="zigzag", height_mm=0.3, position_tip=None,
  enabled=True)`, plus the `turbulator` parameter on `WingSegment` and
  `WingConfiguration`.
  - Legacy origin:
    `cad_designer/airplane/aircraft_topology/wing/Turbulator.py`; gh-934
    approved exception to ADR 0002
  - Definition of done: a `WingConfiguration` round-trip preserves the
    turbulator; a comment records that this is the sanctioned exception to the
    frozen-topology rule so a future reviewer does not "fix" it.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path:** `PUT` a turbulator with `position_root = 0.35` and
      read back `form = "zigzag"`, `height_mm = 0.3`, `enabled = true`,
      effective tip `0.35` (see [`requirements.md`](requirements.md) Acceptance
      Criteria).
- [ ] **TT-02 — Failure:** a turbulator write to the terminal station → 422
      `validation_error`.
- [ ] **TT-03 — Schema matrix:** missing `position_root` → 422;
      `position_root = 1.2` → 422; `position_tip = -0.1` → 422;
      `height_mm = -0.1` → 422; `height_mm = 0` → 200; unknown `form` → 422.
- [ ] **TT-04 — Tip fallback:** omitted `position_tip` resolves to
      `position_root`; an explicit `position_tip` is preserved.
- [ ] **TT-05 — Toggle:** `enabled = false` retains the row and its positions;
      the CAD build omits the strip.
- [ ] **TT-06 — Grid membership:** `xtr_opt` is always one of the 15 values of
      `linspace(0.2, 0.9, 15)`, over many synthetic sweeps.
- [ ] **TT-07 — Baseline:** `cd_clean` is computed with `xtr_upper = 1.0`;
      `delta_cd == cd_tripped − cd_clean`; a beneficial trip yields a **negative**
      `delta_cd`.
- [ ] **TT-08 — Partial NaN:** NaNs at indices 0, 3 and 14 still yield a finite
      `xtr_opt` chosen from the remaining values.
- [ ] **TT-09 — All-NaN:** warning emitted, `xtr_opt` absent, **no fallback
      value anywhere in the payload** (the anti-fallback assertion).
- [ ] **TT-10 — Confidence gate:** mean `0.7` → result **plus** warning; mean
      `0.85` → no warning; a case where the *minimum* is below 0.80 but the
      *mean* is above pins that the gate uses the mean.
- [ ] **TT-11 — Boundary optimum:** index 0 and index 14 each produce the
      warning, still report their value, and leave `XTR_GRID` unextended.
- [ ] **TT-12 — Roll-up:** `ΔCD0 == 2 · Σ(Δcd_i · S_i) / S_ref` for a symmetric
      wing, with a companion assertion that the factor is applied exactly once.
- [ ] **TT-13 — Cascade:** deleting the station removes the turbulator; deleting
      the turbulator leaves the station.
- [ ] **TT-14 — Round-trip:** a turbulator survives a
      model → `WingConfiguration` → model conversion with all five fields
      intact.
- [ ] **TT-15 — Degraded platform:** with the surrogate unimportable, turbulator
      CRUD still returns 200. Pin the optimise route's behaviour explicitly.

## Data Migration Tasks

- [ ] **TM-01 — Backfill `enabled` on any pre-gh-934 rows.** The column is
      `NOT NULL DEFAULT True`; confirm the migration wrote `True` rather than
      leaving the table empty of the column. 🟡 (Low risk — gh-934 introduced the
      table, so there are unlikely to be older rows.)
- [ ] **TM-02 — Sweep for `NULL position_root`.** The column is nullable while
      the schema requires the field, so a row written outside the API would fail
      validation on read. Identify and repair any such rows before enabling a
      strict read path. 🟡

## Suggested Order

1. **T-01 → T-02** first: the table and its schema. T-02 carries most of this
   use case's behaviour (defaults, ranges, the tip fallback), so it is worth
   exhaustively testing before any route exists.
2. **T-03 → T-04** next: CRUD on top of the model. T-03 blocks on the
   `cross-section-crud` terminal guard existing.
3. **T-05 → T-07** as **pure functions against a stubbed surrogate**: the
   constants, the baseline and the sweep are deterministic given a `cd`
   callable, so stub it and test the selection logic in isolation. T-07 blocks
   on T-05 and T-06.
4. **T-08 → T-10** immediately after T-07, and treated as first-class behaviour
   rather than error handling — under ADR 0012 the warnings *are* the product.
   All three are independent of each other and can proceed in parallel.
5. **T-11** once T-07 produces `Δcd_i` — it needs section areas from
   `section_aoa_service`, so it blocks on that service (or a stub of it).
6. **T-12** last of the optimiser chain: the route is thin orchestration over
   T-06…T-11 and should introduce no new decision logic.
7. **T-13** alongside T-12 — the import probe only matters once there is a route
   that would otherwise fail at import time.
8. **T-14** independently at any point; it blocks the CAD build but nothing in
   this use case's own chain.

## Pending Gaps (🔴)

- **Is the optimiser result ever persisted?** No write-back of `xtr_opt` into
  `wing_xsec_turbulators` was captured. If adoption is manual (consistent with
  ADR 0007, "copilot proposes, human adopts"), the UI needs an explicit apply
  step; if it is automatic somewhere, the propose/adopt boundary is being
  crossed silently.
- **What does `POST /turbulator/optimize` return without AeroSandbox /
  NeuralFoil?** On `linux/aarch64` the surrogate is unavailable (ADR 0017). A
  500, an empty result, or a platform warning are all plausible — and only the
  last is consistent with ADR 0012.
- **How is `symmetry_factor` chosen?** Documented as `2` "for a symmetric wing",
  but whether the code reads `wings.symmetric` or infers it from the section
  list was not captured. A vertical stabiliser is exactly where this goes wrong,
  and a doubled `ΔCD0` is invisible in the output.
- **`height_mm` and `form` do not enter the drag model.** The optimiser sweeps
  position only, while trip height and trip form are physically what determine
  whether transition is actually forced. Is the reported optimum meant to be read
  as conditional on an unmodelled height/form, and should that caveat be in the
  response (as the airfoil-catalog contract does with its explicit `caveat`
  block)?
- **How does one `xtr_opt` per section map onto a per-segment `position_root` /
  `position_tip` pair?** The stored turbulator supports a tapered strip; the
  optimiser reports a single value per section. The mapping is unspecified.
- **Does an out-of-range operating `CL` produce a NaN or a silent clamp?**
  `_ALPHA_GRID` spans `[-4°, 14°]`; a section whose `CL` falls outside the
  corresponding range cannot be looked up. If it clamps, the "optimum" is for a
  different operating point than requested.
- **No cost instrumentation.** `15 × sections + sections` surrogate calls per
  request with no timing signal.
