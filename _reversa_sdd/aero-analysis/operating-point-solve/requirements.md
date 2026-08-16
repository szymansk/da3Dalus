# operating-point-solve

> Use-case specification, nested under the module
> [`aero-analysis`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aero-analysis
> (solver dispatcher, R11–R13, Trim enrichment), `_reversa_sdd/domain.md`
> BR-19/BR-20, `_reversa_sdd/data-dictionary.md` §`operating_points`.

## Overview

`operating-point-solve` is the path from *"analyse this aircraft at this flight
condition"* to a numeric answer. It resolves a stored (or inline) operating
point into a coherent, validated analysis state, dispatches it to exactly one
solver, trims one control to a target coefficient when asked, and enriches every
trim with reserves, effectiveness, stability classification and design warnings.
It is the only place where the radian↔degree boundary, the deflection-source
precedence and the deflection-name validation live. 🟢

## Responsibilities

- Resolve an `operating_point_id` into an analysis-ready schema, constrained to
  the aircraft, with `alpha`/`beta` converted from radians to degrees. 🟢
- Choose the deflection source: a **non-empty** manual override beats the
  solver's `controls`; an empty override is a no-op. 🟢
- Validate every deflection name against the ASB airplane before it reaches
  `with_control_deflections`. 🟢
- Dispatch a single point to AeroBuildup, the in-process VLM or AVL, always
  setting the moment reference from `xyz_ref`. 🟢
- Trim one control variable to a target coefficient by bracketed Brent
  root-find, reporting non-convergence instead of raising. 🟢
- Enrich the result: deflection reserves, control effectiveness, stability
  classification, mixer decomposition, and structured design warnings. 🟢
- Persist a trimmed operating point (status, `controls`, `trim_enrichment`,
  `warnings`). 🟢

**Explicitly NOT this use case's responsibility:** generating the 15-target
sweep (→ [`../../mission-and-sizing/operating-point-sweep/`](../../mission-and-sizing/operating-point-sweep/requirements.md)),
the background re-trim of DIRTY rows
(→ [`../retrim-invalidation/`](../retrim-invalidation/requirements.md)), the
cached aero context (→ [`../aero-context-single-source/`](../aero-context-single-source/requirements.md)),
and emitting or running `.avl` files (→ `avl-integration`).

## Business Rules

> Global ids (`BR-*`) are inherited verbatim from
> [`../../domain.md`](../../domain.md); `BR-AA*` from
> [`../requirements.md`](../requirements.md).

- **BR-19 — Trim must reflect one coherent state (gh-577).** 🟢
  `resolve_operating_point` (`operating_point_resolver.py:138-213`) is the guard
  that makes a Trefftz / streamline / strip-force run reflect one trim state:

  | Condition | Behaviour |
  |---|---|
  | no `operating_point_id` | the inline schema passes through — explicit diagnostic / manual mode |
  | with an id | the row is loaded **constrained to `aircraft_pk`**, preventing cross-aeroplane OP injection |
  | status ≠ `TRIMMED` | rejected, unless the caller passed `require_trimmed=False` |
  | conversion | `operating_point_model_to_schema` — the **single** place `alpha`/`beta` go radians → degrees |
  | NULL in a NOT-NULL column | `_require_field` **raises**; it never substitutes `0.0` |

- **BR-AA24 — Deflection-source precedence.** 🟢 `_pick_deflections`: a
  **non-empty** `control_deflections` (manual override) wins; otherwise
  `controls` (the trim solver's output). An **empty** override dict is treated as
  a no-op precisely so it cannot silently erase a fresh trim.
- **BR-20 — Unknown deflection names are a 422, not a silent drop.** 🟢
  `Airplane.with_control_deflections` silently ignores unknown keys, which would
  let a renamed surface run clean while the UI labelled the plot "trimmed".
  `validate_deflections_against_airplane` raises a 422 listing unknown vs
  available names. Called from the streamline, four-view, strip-force and
  AeroBuildup-trim paths.
- **BR-AA22 — The schema guards the rad/deg trap.** 🟢 A field validator rejects
  any `|alpha|` or `|beta| > 180` with the message "almost certainly means
  radians were passed instead of degrees (gh-577/gh-587)".
- **BR-AA1 — One dispatcher, one envelope.** 🟢 See
  [`../requirements.md`](../requirements.md). The moment reference is always set
  from `operating_point.xyz_ref` **before** the solve; on the persisted rows it
  is `[design_cg_x, 0, 0]`.
- **BR-AA19 — The AeroBuildup trim is a bracketed Brent root-find that reports
  non-convergence.** 🟢 `scipy.optimize.brentq`, `xtol=1e-6`, `maxiter=50`, on
  `residual(δ) = coeff(δ) − target`, one
  `AeroBuildup.run_with_stability_derivatives()` per evaluation. When
  `f(lower)·f(upper) > 0` the root is not bracketed and the service returns
  `converged=False` with a detailed warning **instead of raising**.
  Trim-variable resolution accepts the tagged name, the display name **or** a
  role name; a role resolves to that surface's **primary (pitch/lift)** axis,
  because AeroBuildup can only trim the symmetric axis (gh-772).
- **BR-AA20 — Enrichment thresholds are fixed, reported and never clamped.** 🟢

  ```
  usage_fraction = |δ| / (max_pos if δ ≥ 0 else max_neg)     default limits (25, 25)
    > 0.95 → critical  "near mechanical limit"
    > 0.80 → warning   "surface may be undersized"
  trim_score > 0.5 → critical "failed to converge";  > 0.1 → warning
  LIMIT_REACHED    → critical "optimizer hit a constraint boundary"
  static_margin = −Cm_a / CL_a
    ≤ 0    → critical  (statically unstable)
    < 0.05 → warning   (marginal)
    > 0.30 → warning   (very nose-heavy)
  aerobuildup + mixed surfaces → warning: roll/yaw of mixed surfaces is AVL-only
  ```

- **BR-AA25 — Every geometry surface is reported, not only the trimmed one
  (gh-863).** 🟢 `surface_deflections = dict.fromkeys(limits, 0.0)` updated with
  `controls`, so an untrimmed surface appears at `0.0` rather than vanishing.
- **BR-10 — `differential_ratio` is a reporting-only kinematic.** 🟢
  `decompose_dual_role` applies it **after** trim, to the up-going side only; it
  never alters the aero or trim solution:

  ```
  d_sym  = mix_gain_primary   · δ_primary        # pitch / lift axis
  d_anti = mix_gain_secondary · δ_secondary      # roll / yaw axis
  right  =  d_anti ;  left = −d_anti
  the negative (up-going) side is scaled by differential_ratio
  deflection_left/right = d_sym + left/right     # differential never scales d_sym
  ```

- **BR-AA26 — `trim_residuals` is `dict[str, float]` — floats only (gh-627).**
  🟢 The solver path belongs on `trim_method`. A
  `best_residuals["solver_path"] = "opti"` line once broke every OP enrichment
  because Pydantic rejects the string.
- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged. Previously BR-13 (open bug
  #955).** `build_deflection_limits_from_schema`
  (`trim_enrichment_service.py:72-118`) keys `limits` by the **raw TED name from
  the DB**, while `controls` carries mixing names such as
  `[ruddervator]pitch_htail_1`. Consequences on any dual-role aircraft:
  1. `limits.get(name, (25.0, 25.0))` misses ⇒ the reserve is computed against a
     **hard-coded ±25°**, not the aircraft's real hinge limit;
  2. the gh-863 union injects a **phantom surface at 0°** under the DB name that
     no solver ever trims.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Resolve a stored OP constrained to its aircraft | Must | An id from another aeroplane is not found; no analysis runs |
| RF-02 | Require status `TRIMMED` unless explicitly waived | Must | A `DIRTY` OP is rejected; `require_trimmed=False` accepts it |
| RF-03 | Convert stored `alpha`/`beta` from radians to degrees exactly once | Must | `0.0873 rad` reads back as `5.0 deg`; no second conversion downstream |
| RF-04 | Prefer a non-empty manual deflection override; treat `{}` as a no-op | Must | `{}` leaves `controls` in force; `{"elevator": 3}` overrides it |
| RF-05 | Raise rather than substitute `0.0` for a NULL NOT-NULL column | Must | A corrupt row raises; it does not analyse at zero |
| RF-06 | Reject unknown deflection names with 422 listing unknown vs available | Must | `{"aileron_typo": 5}` → 422 with both name sets in the body |
| RF-07 | Reject `\|alpha\|` or `\|beta\| > 180` as a radian/degree mix-up | Must | `alpha = 0.0873` is accepted (0.09°); `alpha = 200` is 422 |
| RF-08 | Set the moment reference from `xyz_ref` before every solve | Must | `Cm` changes with `xyz_ref[0]`, geometry unchanged |
| RF-09 | Dispatch to AeroBuildup, VLM or AVL and return one `AnalysisModel` | Must | The three tools produce the same field set, differing `method` |
| RF-10 | Trim one control to a target coefficient by bracketed Brent root-find | Must | `Cm → 0` within `xtol = 1e-6`, ≤ 50 iterations |
| RF-11 | Report non-convergence structurally, never by raising | Must | An unbracketed root → `converged=false` + warning, HTTP 200 |
| RF-12 | Resolve a trim variable from tagged name, display name or role | Must | Role `elevator` resolves to that surface's primary (pitch) axis |
| RF-13 | Enrich every trim with reserves, effectiveness, stability class, mixer values, warnings | Must | All six blocks present on a converged trim |
| RF-14 | Report every geometry surface, including untrimmed ones at `0.0` | Should | A 3-surface aircraft trimmed on one reports 3 entries |
| RF-15 | Decompose a dual-role trim into physical left/right angles | Should | `differential_ratio` scales only the up-going side, never `d_sym` |
| RF-16 | Keep `trim_residuals` numeric-only | Must | A string value fails schema validation |
| RF-17 | Persist a trimmed OP with `status`, `controls`, `trim_enrichment`, `warnings` | Must | A re-read returns the same trim state |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Cross-aeroplane OP injection is structurally impossible (the query is constrained to `aircraft_pk`) | `operating_point_resolver.py:138-213` | 🟢 |
| Correctness | The rad→deg conversion exists in exactly one function | `operating_point_model_to_schema` | 🟢 |
| Correctness | Unknown deflection names cannot be silently dropped | `validate_deflections_against_airplane` (BR-20) | 🟢 |
| Robustness | An unbracketed trim returns a structured non-convergence rather than a 500 | `aerobuildup_trim_service` | 🟢 |
| Robustness | Enrichment is computed best-effort — an enrichment failure never fails the trim response | AVL/ABU trim endpoints | 🟢 |
| Performance | One `AeroBuildup.run_with_stability_derivatives()` per Brent evaluation, bounded by `maxiter = 50` | `aerobuildup_trim_service` | 🟢 |
| Observability | Non-convergence carries a detailed warning naming the bracket and the residual signs | same | 🟢 |
| Interoperability | NaN/Inf serialise as `null` on the analysis router | `NonFiniteSafeJSONResponse` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Coherent operating-point resolution

  Scenario: A stored trimmed point is resolved in degrees
    Given a TRIMMED operating point with alpha 0.0873 radians
    When it is resolved for analysis
    Then the analysis schema reports alpha 5.0 degrees
    And the deflections used are its controls dict

  Scenario: An empty override cannot erase a fresh trim
    Given a TRIMMED operating point with controls {"elevator": -3.2}
    And control_deflections set to an empty dict
    When it is resolved
    Then the deflections used are {"elevator": -3.2}

  Scenario: A manual override wins
    Given the same operating point with control_deflections {"elevator": 1.0}
    When it is resolved
    Then the deflections used are {"elevator": 1.0}

  Scenario: Cross-aeroplane injection is refused
    Given an operating point id that belongs to a different aeroplane
    When it is resolved for this aircraft
    Then the row is not found
    And no solver runs

  Scenario: An untrimmed point is refused by default
    Given a DIRTY operating point
    When it is resolved with require_trimmed left at its default
    Then the request fails
    But it succeeds when require_trimmed is false

Feature: Deflection validation

  Scenario: An unknown surface name is rejected
    Given an aircraft whose control surfaces are "elevator" and "aileron"
    When I request an analysis with control_deflections {"elevater": 4.0}
    Then the response status is 422
    And the body lists "elevater" as unknown and both real names as available

  Scenario: Radians passed as degrees are caught by the schema
    Given a request body with alpha 200
    When it is validated
    Then the response status is 422
    And the message mentions radians being passed instead of degrees

Feature: AeroBuildup trim

  Scenario: A pitch trim converges
    Given a trimmable aircraft and a target Cm of 0
    When I trim on the elevator between -25 and 25 degrees
    Then converged is true
    And |Cm| at the returned deflection is below the solver tolerance

  Scenario: An unbracketed root reports itself
    Given an aircraft whose Cm has the same sign at both deflection bounds
    When I request the trim
    Then the response status is 200
    And converged is false
    And a warning describes the unbracketed interval
    And no exception propagates

  Scenario: A role name resolves to the primary axis
    Given a ruddervator whose axes are pitch (primary) and yaw (secondary)
    When I trim with the variable "ruddervator"
    Then the pitch axis control variable is trimmed
    And the yaw axis is untouched

Feature: Trim enrichment

  Scenario: A near-limit deflection is critical
    Given a surface with limits (25, 25) trimmed to -24.5 degrees
    When the enrichment is computed
    Then usage_fraction exceeds 0.95
    And a critical warning of category "authority" names that surface

  Scenario: An undersized surface is a warning, not a failure
    Given the same surface trimmed to -21 degrees
    Then usage_fraction is above 0.80 and below 0.95
    And a warning-level authority message is emitted

  Scenario: Untrimmed surfaces still appear
    Given three control surfaces and a trim solved on one
    When the enrichment is computed
    Then three surface deflections are reported
    And the two untrimmed ones are 0.0

  Scenario: Differential never touches the symmetric part
    Given a dual-role surface with d_sym 6 degrees, d_anti 4 degrees and differential_ratio 1.5
    When the mixer values are computed
    Then the up-going side is scaled by 1.5
    And the symmetric offset stays 6 degrees

  Scenario: A string residual is rejected
    Given a trim result whose residuals contain "solver_path": "opti"
    When the enrichment is validated
    Then validation fails
    # gh-627 — the solver path belongs on trim_method

  Scenario: A dual-role aircraft falls back to the wrong limits today
    Given a ruddervator whose control variable is "[ruddervator]pitch_htail_1"
    And deflection limits keyed by the DB name "ruddervator_right"
    When the enrichment is computed
    Then the reserve is computed against the hard-coded (25, 25) limits
    And a phantom surface at 0 degrees appears under the DB name
    # 🟢 resolved structurally (Q-WD-1)
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| OP resolution with the four guards (RF-01…RF-05) | Must | BR-19; without it a chart can claim a trim state the numbers never had |
| Deflection-name validation (RF-06) | Must | BR-20; ASB drops unknown keys silently — the failure is invisible otherwise |
| Rad/deg guard (RF-07) | Must | A 57× error that produces plausible-looking output |
| Dispatch + moment reference (RF-08, RF-09) | Must | Every analysis path funnels through it |
| Brent trim with structured non-convergence (RF-10…RF-12) | Must | The default trim engine; used by the background retrim too |
| Enrichment core (RF-13, RF-16, RF-17) | Must | The only control-authority check in the system |
| Full-surface reporting (RF-14) | Should | A completeness improvement (gh-863) over reporting only the trimmed surface |
| Dual-role decomposition (RF-15) | Should | Display-only kinematics (BR-10); does not affect the solution |
| Keying enrichment limits by the mixing name | **Must (open)** | Bug #955 — today every V-tail / elevon aircraft gets a wrong authority verdict |
| Trimming the antisymmetric axis with AeroBuildup | Won't | ASB models one axis; AVL only (ADR 0003) |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/operating_point_resolver.py` | `resolve_operating_point`, `operating_point_model_to_schema`, `_pick_deflections`, `_require_field`, `validate_deflections_against_airplane` | 🟢 |
| `app/api/utils.py` | `analyse_aerodynamics`, `_as_array_if_needed` | 🟢 |
| `app/services/aerobuildup_trim_service.py` | `trim_with_aerobuildup`, name resolution | 🟢 |
| `app/services/trim_enrichment_service.py` | `compute_enrichment` (`:380-572`), `build_deflection_limits_from_schema` (`:72-118`), `decompose_dual_role` | 🟢 / 🔴 (#955) |
| `app/schemas/aeroanalysisschema.py` | `OperatingPointSchema` (`:231`), `TrimEnrichment`, `DeflectionReserve`, `DesignWarning`, `ControlEffectiveness`, `StabilityClassification`, `MixerValues` | 🟢 |
| `app/models/analysismodels.py` | `OperatingPointModel` | 🟢 |
| `app/api/v2/endpoints/operating_points.py` | `trim_operating_point`, `aerobuildup_trim_operating_point`, `patch_operating_point_deflections`, CRUD | 🟢 |
| `app/api/v2/endpoints/aeroanalysis.py` | `analyze_wing_post`, `analyze_airplane_post` | 🟢 |
