# turbulator-optimizer

> Use-case specification, nested under the module [`wing-design`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: wing-design
> (Turbulator optimiser, gh-934), `_reversa_sdd/data-dictionary.md`
> §Module: wing-design, ADR 0012.

## Overview

`turbulator-optimizer` owns the per-segment **turbulator** — a forced-transition
trip strip (zigzag, dots or thread) applied to the upper surface — and the
optimiser that finds, per wing section, the trip location minimising section
drag at that section's operating `(CL, Re)`. It is an optional refinement: an
aircraft is complete without one. Unphysical optimiser results surface as
**design warnings, never silent fallbacks**. 🟢

## Responsibilities

- CRUD for the per-segment turbulator (`GET` / `PUT` / `DELETE`), rejecting
  writes to the terminal station. 🟢
- Store `form`, `height_mm`, `position_root`, `position_tip` and `enabled`. 🟢
- Sweep a grid of forced-transition locations per section and pick the one
  minimising `cd` at the section's operating `(CL, Re)`. 🟢
- Report the per-section `xtr_opt` and `delta_cd` against a natural-transition
  baseline. 🟢
- Roll the per-section drag deltas up into an aircraft-level `ΔCD0`, applying
  the symmetry factor. 🟢
- Emit explicit warnings for an all-NaN sweep, low analysis confidence, and a
  boundary optimum — never substitute a fallback value. 🟢

**Explicitly NOT this use case's responsibility:** the station/segment model and
the terminal-station guard itself (→ [`../cross-section-crud/`](../cross-section-crud/requirements.md)),
the spar pipeline (→ [`../spar-sizing/`](../spar-sizing/requirements.md)),
control surfaces (→ [`../control-surface-mixing/`](../control-surface-mixing/requirements.md)),
computing the per-section angle of attack (→ `section_aoa_service` in
`aero-analysis`), and rendering the trip strip in CAD (→ `cad-generation`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-W14 — The turbulator optimiser minimises section drag at the section's
  operating `(CL, Re)` (gh-934).** 🟢 *(module-level BR-W14; this use case is
  its owner.)*

  ```
  XTR_GRID              = linspace(0.2, 0.9, 15)     # x/c sweep       (l.53)
  _ALPHA_GRID           = linspace(-4.0, 14.0, 37)   # cd-at-CL lookup (l.60)
  _CONFIDENCE_THRESHOLD = 0.80                       # warning gate    (l.56)

  cd_clean = cd(CL, Re, xtr_upper = 1.0)             # natural-transition baseline
  i_opt    = argmin over FINITE cd values
  xtr_opt  = XTR_GRID[i_opt]
  delta_cd = cd_tripped − cd_clean

  ΔCD0 = symmetry_factor · Σ (Δcd_i · S_i) / S_ref
         symmetry_factor = 2 for a symmetric wing
         (section_aoa_service returns half-span sections only)
  ```

  `xtr_upper = 1.0` means "no forced transition" — transition happens naturally,
  which is why it is the clean baseline. A **negative** `delta_cd` is an
  improvement.
- **BR-W15 — Unphysical optimiser results surface as warnings, never silent
  fallbacks.** 🟢 *(ADR 0012.)* Warnings are emitted for:
  1. **all-NaN `cd`** — no optimum exists for that section;
  2. **mean `analysis_confidence < 0.80`** — the surrogate is not trustworthy at
     this operating point;
  3. **a boundary optimum** — `i_opt ∈ {0, len−1}`, meaning the true minimum may
     lie outside `[0.2, 0.9]`.
  (`app/services/turbulator_optimizer_service.py:223-268, 294-331`.) No fallback
  value is substituted in any of the three cases.
- **BR-T1 — The turbulator is segment-scoped, 1:1 with the inboard station.** 🟢
  *(refines BR-4/BR-5.)* `wing_xsec_turbulators.wing_xsec_detail_id` is FK
  `ON DELETE CASCADE` and **unique**
  (`app/models/aeroplanemodel.py:83`). A write targeting the terminal station is
  rejected with 422 by `_assert_non_terminal_xsec_or_raise`
  (`app/services/wing_service.py:151-156`).
- **BR-T2 — Turbulator fields and their schema defaults.** 🟢
  (`app/models/aeroplanemodel.py:83`, `app/schemas/aeroplaneschema.py:233`.)

  | Field | Column | Schema |
  |---|---|---|
  | `form` | String, nullable | `zigzag` \| `dots` \| `thread`, default **`zigzag`** |
  | `height_mm` | Float, nullable | **mm**, default **`0.3`**, constraint `≥ 0` |
  | `position_root` | Float, nullable | x/c `∈ [0, 1]`, **required** in the schema |
  | `position_tip` | Float, nullable | x/c `∈ [0, 1]`; **falls back to `position_root`** |
  | `enabled` | Boolean, **`NOT NULL`** | default **`True`** — whether it is rendered in CAD |

  Note the asymmetry: the columns are nullable while the schema makes
  `position_root` required and supplies the other defaults — the standard
  "validate above the topology layer" split (ADR 0002).
- **BR-T3 — `Turbulator` is the one permitted addition to the frozen topology
  layer.** 🟢 The `cad_designer` topology is read-only (ADR 0002), but gh-934
  required extending `WingSegment` and `WingConfiguration` to accept a
  `turbulator` parameter. This is an explicitly approved exception, recorded so
  it is not mistaken for a violation. Topology signature:
  `Turbulator(position_root, form="zigzag", height_mm=0.3, position_tip=None,
  enabled=True)`.
- **BR-T4 — The optimiser reads half-span sections and doubles them.** 🟢
  `section_aoa_service` returns **half-span sections only**, so the aircraft-level
  roll-up applies `symmetry_factor = 2` for a symmetric wing. Applying it to an
  asymmetric surface, or double-counting an already-full-span section list,
  would silently double `ΔCD0`.
- **BR-T5 — The optimiser is a read-only analysis.** 🟡 INFERRED.
  `POST /aeroplanes/{id}/turbulator/optimize` returns per-section results; the
  source analysis records no write-back of `xtr_opt` into
  `wing_xsec_turbulators`. Adopting a suggested position appears to be a separate,
  explicit act by the user (consistent with ADR 0007, "copilot proposes, human
  adopts"). 🟢 **Confirmed by code lookup** (`Q-WD-10`): `optimize_turbulator`
  (`turbulator_optimizer.py:184-199`) calls `_call_optimizer` then
  `_result_to_response` **with no DB write in between**, and the only writers of
  `position_root` / `position_tip` in `app/` are ordinary wing CRUD
  (`wing_service.py:1541`, `aeroplanemodel.py:401`) and the version clone
  (`aeroplane_clone_service.py:279-284`). The propose/adopt boundary is not
  crossed. Stored positions are read in the other direction only, by the
  assumption pipeline's `cd0` adjustment
  (`assumption_compute_service.py:2236-2237`).

## Functional Requirements

> The `RF-xx` ids refine the module-level requirements in
> [`../requirements.md`](../requirements.md).

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-13 | Turbulator CRUD per segment (`GET` / `PUT` / `DELETE`) | Should | `PUT .../turbulator` with `position_root = 0.35` → 200; the same write on the terminal station → 422 |
| RF-22 | Optimise the turbulator position per section and report `ΔCD0` with warnings | Should | `POST /aeroplanes/{id}/turbulator/optimize` → 200 with per-section `xtr_opt`, `delta_cd` and any boundary/confidence warnings |
| RF-T1 | Apply the schema defaults on a partial turbulator write | Should | A write omitting `form` and `height_mm` stores `zigzag` and `0.3` |
| RF-T2 | Fall back `position_tip` to `position_root` | Should | A write with `position_root = 0.35` and no `position_tip` yields an effective tip position of `0.35` |
| RF-T3 | Reject an out-of-range position or a negative height | Should | `position_root = 1.2` → 422; `height_mm = -0.1` → 422; `height_mm = 0` → 200 |
| RF-T4 | Require `position_root` | Should | A turbulator write with no `position_root` → 422 |
| RF-T5 | Restrict `xtr_opt` to the sweep grid | Must | `xtr_opt` is always one of the 15 values of `linspace(0.2, 0.9, 15)` |
| RF-T6 | Compute `delta_cd` against a natural-transition baseline | Must | `delta_cd == cd_tripped − cd_clean`, where `cd_clean = cd(CL, Re, xtr_upper = 1.0)` |
| RF-T7 | Ignore non-finite `cd` values when selecting the optimum | Must | A sweep containing NaNs picks the argmin over the **finite** values only |
| RF-T8 | Warn on an all-NaN sweep and emit no optimum | Must | A section whose sweep is entirely NaN reports a warning and **no** `xtr_opt`; no fallback value is substituted |
| RF-T9 | Warn when mean analysis confidence is below 0.80 | Must | A section whose mean `analysis_confidence` is `0.7` returns its result **plus** a confidence warning |
| RF-T10 | Warn on a boundary optimum | Must | `i_opt ∈ {0, 14}` yields a warning stating the true minimum may lie outside `[0.2, 0.9]`, and the boundary value is still reported |
| RF-T11 | Roll per-section deltas up into `ΔCD0` with the symmetry factor | Must | `ΔCD0 == 2 · Σ(Δcd_i · S_i) / S_ref` for a symmetric wing |
| RF-T12 | Toggle CAD rendering without deleting the turbulator | Should | `enabled = false` keeps the row but excludes the trip strip from the CAD build |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Robustness | Optimiser anomalies (all-NaN, low confidence, boundary optimum) become explicit warnings rather than substituted values | `turbulator_optimizer_service.py:223-268, 294-331` (ADR 0012) | 🟢 |
| Correctness | The optimum is selected over **finite** `cd` values only, so a partially failed sweep still yields a usable answer | `turbulator_optimizer_service.py` (`i_opt = argmin over FINITE cd values`) | 🟢 |
| Correctness | The baseline is a genuine natural-transition run (`xtr_upper = 1.0`), not the first grid point, so `delta_cd` is a true improvement measure | `turbulator_optimizer_service.py` (`cd_clean`) | 🟢 |
| Correctness | The half-span-only convention of `section_aoa_service` is compensated by an explicit `symmetry_factor`, not assumed away | `turbulator_optimizer_service.py` (ΔCD0 roll-up) | 🟢 |
| Performance | The sweep is bounded to a fixed 15-point `x/c` grid and a fixed 37-point α grid, so cost per section is constant and predictable | `turbulator_optimizer_service.py:53, 60` | 🟢 |
| Integrity | The turbulator row is 1:1 with the segment detail and cascades on delete | `aeroplanemodel.py:83` | 🟢 |
| Portability | The optimiser depends on the NeuralFoil surrogate; consumers of AeroSandbox must import defensively on `linux/aarch64` | cross-module platform note; ADR 0017 | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Turbulator CRUD

  Scenario: A turbulator is written to a segment
    Given a wing with 3 stations
    When I PUT cross_sections index 0 turbulator with position_root 0.35
    Then the response status is 200
    And the stored row has form "zigzag", height_mm 0.3 and enabled true

  Scenario: Writing a turbulator to the terminal station is rejected
    Given a wing with 3 stations
    When I PUT cross_sections index 2 turbulator with position_root 0.35
    Then the response status is 422
    And the error code is "validation_error"

  Scenario: The tip position falls back to the root position
    Given a turbulator written with position_root 0.35 and no position_tip
    When I read the turbulator back
    Then the effective tip position is 0.35

  Scenario: position_root is required
    Given a turbulator payload with no position_root
    When I PUT the turbulator
    Then the response status is 422

  Scenario: Out-of-range values are rejected
    Given a turbulator payload with position_root 1.2
    When I PUT the turbulator
    Then the response status is 422
    And a payload with height_mm -0.1 is also rejected
    And a payload with height_mm 0 is accepted

  Scenario: Disabling keeps the row
    Given a segment with a turbulator
    When I PUT the turbulator with enabled false
    Then the response status is 200
    And the row still exists
    And the CAD build omits the trip strip

Feature: Turbulator optimisation

  Scenario: A section gets an optimal trip location
    Given a wing section with a valid operating CL and Re
    When I POST /aeroplanes/{id}/turbulator/optimize
    Then xtr_opt is one of the 15 grid values in [0.2, 0.9]
    And delta_cd equals cd_tripped minus cd_clean
    And cd_clean was computed with xtr_upper 1.0

  Scenario: The aircraft-level drag delta applies the symmetry factor
    Given a symmetric wing whose half-span sections have deltas and areas
    When the optimisation completes
    Then delta_CD0 equals 2 times the sum of delta_cd_i times S_i divided by S_ref

  Scenario: NaN values are skipped rather than poisoning the argmin
    Given a sweep in which some grid points return NaN cd
    When the optimum is selected
    Then the argmin is taken over the finite values only
    And a finite xtr_opt is returned

  Scenario: An all-NaN section reports no optimum
    Given a section whose entire cd sweep is NaN
    When the optimisation completes
    Then a warning states that no optimum could be found
    And no xtr_opt is reported
    And no fallback value is substituted

  Scenario: Low confidence is flagged, not hidden
    Given a section whose mean analysis_confidence is 0.7
    When the optimisation completes
    Then the result is still returned
    And a warning states the analysis confidence is below 0.80

  Scenario: A boundary optimum is flagged, not hidden
    Given the minimum cd occurs at the first or last grid point
    When the optimisation completes
    Then a warning states the true minimum may lie outside [0.2, 0.9]
    And the boundary value is still reported
    And no fallback value is substituted
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Grid-restricted `xtr_opt` (RF-T5) | Must | The contract of a sweep-based optimiser; an off-grid value would mean the search space was silently changed |
| `delta_cd` against a natural-transition baseline (RF-T6) | Must | Without the correct baseline the reported "improvement" is meaningless |
| Finite-only argmin (RF-T7) | Must | A single NaN would otherwise poison the whole sweep |
| All three warning classes (RF-T8, RF-T9, RF-T10) | Must | ADR 0012 — the explicit project rule that unphysical results become design warnings, never hidden fallbacks |
| `ΔCD0` roll-up with the symmetry factor (RF-T11) | Must | Omitting the factor halves the reported benefit; applying it twice doubles it — and neither is detectable from the number alone |
| Turbulator CRUD (RF-13) | Should | The turbulator is an optional per-segment refinement (gh-934); the aircraft is complete without one |
| Schema defaults and the tip fallback (RF-T1, RF-T2) | Should | Ergonomics — a designer specifies one position and gets a sensible strip |
| Range and required-field validation (RF-T3, RF-T4) | Should | An x/c outside `[0, 1]` is geometrically meaningless |
| `enabled` toggle (RF-T12) | Should | Lets a designer compare with/without a strip without losing the configured position |
| Writing the optimum back into the stored turbulator (Slice 3) | **Should** | 🟢 decided (`Q-WD-10 ①`, maintainer): the optimum flows back into `wing_xsec_turbulators` behind an **explicit "apply" step**, preserving the ADR 0007 boundary. Rationale: the turbulator is a *manufacturable* feature — a `WingCreator` can print it directly into the wing — not merely an analysis parameter |
| Extending the sweep beyond `[0.2, 0.9]` on a boundary hit | Won't | The boundary case is reported as a warning by design; auto-extending would hide it |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/turbulator_optimizer_service.py` | the xtr sweep optimiser; `XTR_GRID` (l.53), `_CONFIDENCE_THRESHOLD` (l.56), `_ALPHA_GRID` (l.60), warning emission (l.223-268, l.294-331) | 🟢 |
| `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py` | `POST /aeroplanes/{id}/turbulator/optimize` (l.173) | 🟢 |
| `app/api/v2/endpoints/aeroplane/wings.py` | `GET` / `PUT` / `DELETE .../cross_sections/{i}/turbulator` | 🟢 |
| `app/models/aeroplanemodel.py` | `WingXSecTurbulatorModel` (l.83) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `TurbulatorDetailSchema` (l.233) — `position_* ∈ [0,1]`, `height_mm ≥ 0` | 🟢 |
| `app/services/wing_service.py` | turbulator CRUD, `_assert_non_terminal_xsec_or_raise` (l.151-156) | 🟢 |
| `app/services/section_aoa_service.py` | supplies half-span section `(CL, Re, S_i)` | 🟡 — the half-span convention is 🟢; the exact interface was not captured |
| `cad_designer/airplane/aircraft_topology/wing/Turbulator.py` | `Turbulator(position_root, form="zigzag", height_mm=0.3, position_tip=None, enabled=True)` | 🟢 — the approved gh-934 exception to ADR 0002 |
