# cg-mass-computation

> Use-case specification, nested under the module
> [`mass-and-balance`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/mass_cg_service.py`,
> `app/api/v2/endpoints/aeroplane/mass_cg.py`, `app/schemas/mass_cg.py`,
> ADR 0011, ADR 0012, ADR 0017. Endpoint contract:
> [`../contracts.md`](../contracts.md).

## Overview

This use case holds the module's **arithmetic**: the mass-weighted CG
aggregation, the top-down CG rule `x_np − SM·MAC`, the design-vs-component CG
comparison with its 1 cm verdict, and the mass-dependent design metrics
(wing loading, stall speed, required C_L, C_L margin). All of it is either a
pure function or a thin resolver on top of one. 🟢

It is the code-level expression of ADR 0011: the *requirement* CG and the
*status* CG are computed by different formulas, and the status is never allowed
to overwrite the requirement. 🟢

## Responsibilities

- `aggregate_weight_items` — total mass and 3-axis mass-weighted CG, or four
  `None`s. 🟢
- `compute_recommended_cg` — the top-down rule `np_x − SM·mac`. 🟢
  (🟢 gains one with `Q-MB-2`.)
- `compute_design_metrics` — the five-input, four-output flight-condition
  metric block with full input validation. 🟢
- `get_cg_comparison` — design CG vs aggregate CG, Δx and the tolerance
  verdict. 🟢
- `get_s_ref_for_aeroplane` — resolve the wing reference area by building the
  AeroSandbox airplane. 🟢
- `get_effective_assumption_value` — the module-local ESTIMATE/CALCULATED
  resolver. 🟢

**NOT this use case:** the inventory rows
(→ [`weight-items`](../weight-items/requirements.md)), the write into the mass
assumption (→ [`component-tree-mass-sync`](../component-tree-mass-sync/requirements.md)),
and the stability solve that produces `x_np` / `MAC` (→ `aero-analysis`).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-MB*` from
> [`../requirements.md`](../requirements.md); `BR-CG*` are new here.

- **BR-MB6 — CG aggregation is mass-weighted, three-axis, and undefined for a
  non-positive total.** 🟢
  ```
  items empty                 -> (None, None, None, None)
  m_tot = Σ mᵢ ;  m_tot ≤ 0   -> (None, None, None, None)
  cg_k  = Σ (mᵢ · kᵢ) / m_tot          k ∈ {x, y, z}
  ```
  (`aggregate_weight_items:78-97`.) The `≤ 0` guard also covers a pathological
  negative inventory.
- **BR-CG1 — The aggregation takes dicts, not rows.** 🟢 Its parameter type is
  `Sequence[WeightItemData]` — a `TypedDict{mass_kg, x_m, y_m, z_m}` (`:24-28`).
  It is therefore pure, DB-free, and reusable for any future mass source. 🟡
- **BR-28 — CG is a top-down design target (ADR 0011).** 🟢
  `compute_recommended_cg(np_x, mac, SM) = np_x − SM·mac`. This is what `cg_x`
  *means*; the aggregate is the status against it.
- **BR-MB7 — The comparison is a delta with a strict 1 cm verdict.** 🟢
  ```
  Δx               = design_cg_x − component_cg_x
  within_tolerance = |Δx| < CG_TOLERANCE_M          CG_TOLERANCE_M = 0.01 m
  ```
  The comparison is strict `<`, so exactly 0.01 m is **outside** tolerance.
- **BR-CG2 — No components means no verdict, not a failed verdict.** 🟢 When
  `cg_x` from the aggregation is `None`, `delta_x` and `within_tolerance` are
  both `None` — never `0.0` / `False` (`get_cg_comparison:235-239`). ADR 0012.
- **BR-MB8 — The design CG is resolved through the raising local resolver.** 🟢
  `get_effective_assumption_value` returns `calculated_value` when
  `active_source == "CALCULATED"` and it is not `None`, else `estimate_value`;
  a missing row raises `NotFoundError(entity="DesignAssumption")` (`:112-128`).
  🟡 `design_assumptions_service.get_effective_assumption` would instead fall
  back to `PARAMETER_DEFAULTS` and return `None`.
- **BR-MB10 — The design-metric formulas.** 🟢
  ```
  W          = mass_kg · GRAVITY               GRAVITY = 9.81
  W/S        = W / s_ref                       [Pa]
  V_stall    = sqrt(2·W / (ρ · s_ref · cl_max))[m/s]
  q          = ½ · ρ · velocity²               [Pa]
  CL_req     = W / (q · s_ref)
  CL_margin  = cl_max − CL_req                 > 0 ⇒ above stall
  ```
- **BR-MB11 — Non-positive inputs are rejected, never clamped.** 🟢 Five
  guards, five distinct messages, all before any arithmetic (`:49-58`).
- **BR-MB12 — A wingless aircraft gets a remediation, not a division by zero.**
  🟢 `get_s_ref_for_aeroplane` raises `ValidationError("Wing reference area
  (s_ref) is zero or negative — add wings first")`; a converter failure becomes
  `InternalError("Could not compute wing reference area: …")` (`:252-268`).
- **BR-CG3 — `s_ref` costs a full airplane build.** 🟢
  `get_s_ref_for_aeroplane` resolves the whole `AeroplaneSchema` and runs
  `aeroplane_schema_to_asb_airplane_async` to read a single attribute. 🟡 No
  caching, no reuse of the gh-924 context's `s_ref_m2` — which the powertrain
  solution space *does* read.
- **BR-MB13 — AeroSandbox is imported inside the function.** 🟢
  `import aerosandbox as asb` in the body of
  `get_design_metrics_for_aeroplane` (`:275`); ρ comes from
  `asb.Atmosphere(altitude).density()` — the ISA model, not the exponential
  approximation used by `powertrain`. ADR 0017.
- **BR-MB9 — `GRAVITY = 9.81`.** 🟢 Diverges from `9.80665` in the powertrain
  and endurance stack. 🟡
- 🟢 **`compute_recommended_cg` gains its production caller** (`Q-MB-2`); the duplicates are removed. The same rule is
  implemented independently in
  `loading_scenario_service.compute_stability_envelope` and
  `assumption_compute_service`.
- 🟢 **They gain a route with `Q-MB-2`.** Previously dead schemas**
  (`app/schemas/mass_cg.py:8-23`).
- 🟢 **`cg_y` / `cg_z` gain consumers** (`Q-MB-3`): aileron-trim band, thrust-line arm. Previously computed, serialised and never read.** Only `cg_x`
  reaches `assumption_computation_context.cg_agg_m`.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Aggregate a list of point masses into total mass and 3-axis CG | Must | 0.4 kg @ (0.10, 0, 0) + 0.6 kg @ (0.20, 0, 0) ⇒ `(1.0, 0.16, 0.0, 0.0)` |
| RF-02 | Return four `None`s for an empty or non-positive-mass input | Must | `[]` and `[{mass_kg: 0, …}]` both ⇒ `(None, None, None, None)` |
| RF-03 | Resolve the effective value of a design assumption | Must | CALCULATED + value ⇒ calculated; CALCULATED + `null` ⇒ estimate; ESTIMATE ⇒ estimate |
| RF-04 | Raise `NotFoundError` for a missing assumption row | Must | Absent `cg_x` row ⇒ 404, not a `PARAMETER_DEFAULTS` fallback |
| RF-05 | Compare the design CG with the aggregate and publish Δx | Must | `GET .../cg_comparison` → 200 with `delta_x = design − component` |
| RF-06 | Publish `within_tolerance` as `|Δx| < 0.01 m`, strictly | Must | `Δx = 0.010` ⇒ `false`; `Δx = 0.0099` ⇒ `true` |
| RF-07 | Report every component field as `null` when there is no aggregate | Must | No weight items ⇒ `component_cg_x/y/z`, `component_total_mass_kg`, `delta_x`, `within_tolerance` all `null`; `design_cg_x` present |
| RF-08 | Compute the four design metrics at a flight condition | Must | `POST .../design_metrics` → 200 with the seven-field response |
| RF-09 | Reject each non-positive metric input with its own message | Must | `mass_kg ≤ 0` ⇒ `"mass_kg must be positive"`; likewise `s_ref`, `cl_max`, `rho`, `velocity` |
| RF-10 | Resolve `s_ref` from the built ASB airplane | Must | An aeroplane with one 0.30 m² wing reports `s_ref ≈ 0.30` |
| RF-11 | Explain a missing wing rather than dividing by zero | Must | Wingless aeroplane ⇒ 422 containing `"add wings first"` |
| RF-12 | Report a conversion failure as an internal error | Must | Converter patched to raise ⇒ 500 `"Could not compute wing reference area: …"` |
| RF-13 | Take ρ from the ISA atmosphere at the requested altitude | Must | `altitude = 1000` yields a lower ρ than `altitude = 0`, and a higher stall speed |
| RF-14 | Provide `compute_recommended_cg` as a pure function | Should | `(0.5, 0.2, 0.12) ⇒ 0.476` |
| RF-15 | Keep the module importable where AeroSandbox is unavailable | Should | Importing `mass_cg_service` with `aerosandbox` absent succeeds; only `design_metrics` fails |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Every derived quantity is either a real number or `None` — no fabricated zeros, no clamps (ADR 0012) | `:49-58, 86-91, 235-239` | 🟢 |
| Correctness | The design CG is read, never written, by this use case (ADR 0011) | `get_cg_comparison:228` | 🟢 |
| Correctness | Validation precedes arithmetic, so no formula ever sees a zero denominator | `compute_design_metrics:49-62` | 🟢 |
| Portability | Heavy dependencies are imported inside the functions that need them (ADR 0017) | `:254-255, 275` | 🟢 |
| Performance | Every function except `get_s_ref_for_aeroplane` is O(n) over the inventory with no DB round-trip | `:78-97` | 🟢 |
| Performance | `design_metrics` is the module's only expensive route — a full ASB airplane build per call, uncached | `:252-268` | 🟡 |
| Usability | A failure states the remediation, not just the symptom (*"add wings first"*) | `:265-267` | 🟢 |
| Testability | The four load-bearing formulas are pure functions with no session argument | `:36, 41, 78` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Mass-weighted CG aggregation

  Scenario: Two items on the x axis
    Given weight items 0.4 kg at x 0.10 and 0.6 kg at x 0.20
    When I aggregate them
    Then the total mass is 1.0
    And cg_x is 0.16
    And cg_y and cg_z are 0.0

  Scenario: An empty list has no aggregate
    Given no weight items
    When I aggregate them
    Then all four returned values are null

  Scenario: A zero total mass has no aggregate
    Given weight items whose masses are all 0
    When I aggregate them
    Then all four returned values are null

Feature: CG comparison

  Scenario: Inside tolerance
    Given a design cg_x of 0.150 m and an aggregate CG of 0.155 m
    When I GET the CG comparison
    Then delta_x is -0.005
    And within_tolerance is true

  Scenario: Exactly at the tolerance is outside it
    Given a design cg_x of 0.150 m and an aggregate CG of 0.140 m
    When I GET the CG comparison
    Then delta_x is 0.010
    And within_tolerance is false

  Scenario: No components means no verdict
    Given an aeroplane with a cg_x assumption and no weight items
    When I GET the CG comparison
    Then design_cg_x is populated
    And component_cg_x, component_total_mass_kg, delta_x and within_tolerance are null

  Scenario: A missing cg_x assumption is a 404
    Given an aeroplane without a cg_x design-assumption row
    When I GET the CG comparison
    Then the response status is 404

Feature: Design metrics

  Scenario: Metrics at sea level
    Given mass 2.0 kg, s_ref 0.30 m², cl_max 1.4, rho 1.225 and velocity 15 m/s
    When I compute the design metrics
    Then wing_loading_pa is 2.0 * 9.81 / 0.30
    And stall_speed_ms is sqrt(2 * 2.0 * 9.81 / (1.225 * 0.30 * 1.4))
    And required_cl is (2.0 * 9.81) / (0.5 * 1.225 * 15**2 * 0.30)
    And cl_margin is 1.4 minus required_cl

  Scenario: Altitude lowers the density and raises the stall speed
    Given the same aircraft
    When I request metrics at altitude 1000 m instead of 0 m
    Then stall_speed_ms is higher

  Scenario Outline: Non-positive inputs are rejected
    Given a design-metric request where <field> is <value>
    When I compute the metrics
    Then a ValidationError is raised with message "<field> must be positive"
    Examples:
      | field   | value |
      | mass_kg | 0     |
      | s_ref   | 0     |
      | cl_max  | -1    |
      | rho     | 0     |
      | velocity| 0     |

  Scenario: An aircraft without wings is refused with a remediation
    Given an aeroplane with no wings
    When I request design metrics
    Then the response status is 422
    And the message contains "add wings first"

Feature: Effective assumption resolution

  Scenario Outline: The resolver follows active_source
    Given an assumption with active_source <source> and calculated_value <calc>
    When I resolve its effective value
    Then the result is <expected>
    Examples:
      | source     | calc | expected       |
      | CALCULATED | 2.4  | 2.4            |
      | CALCULATED | null | estimate_value |
      | ESTIMATE   | 2.4  | estimate_value |

  Scenario: A missing row raises rather than defaulting
    Given no design-assumption row named "mass"
    When I resolve its effective value
    Then a NotFoundError is raised
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| `aggregate_weight_items` (RF-01/RF-02) | Must | The only aggregate-CG implementation; feeds both the comparison and the sync |
| Effective-value resolution (RF-03/RF-04) | Must | Every DB-aware function in the use case starts here |
| CG comparison + strict verdict (RF-05…RF-07) | Must | The user-facing feedback of ADR 0011's design loop |
| Design metrics + input rejection (RF-08/RF-09) | Must | The mass sanity check shown beside the assumption panel |
| `s_ref` resolution with the wingless remediation (RF-10…RF-12) | Must | Without it the metrics divide by zero on every new aircraft |
| ISA density at altitude (RF-13) | Should | Sea level is the default; altitude is an optional refinement |
| Lazy ASB import (RF-15) | Should | Keeps the other six routes alive on ASB-less platforms |
| `compute_recommended_cg` (RF-14) | **Must** | 🟢 single authority with a production caller (`Q-MB-2`); no caller; duplicated twice elsewhere |
| 3-axis CG output | Could | `cg_y` / `cg_z` are published and read by nothing |
| Caching / reusing the context's `s_ref_m2` | Won't | Not implemented — every call rebuilds the airplane |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/mass_cg_service.py:20-21` | `GRAVITY`, `CG_TOLERANCE_M` | 🟢 |
| `app/services/mass_cg_service.py:24` | `WeightItemData` | 🟢 |
| `app/services/mass_cg_service.py:36` | `compute_recommended_cg` | 🟢 (🔴 uncalled) |
| `app/services/mass_cg_service.py:41` | `compute_design_metrics` | 🟢 |
| `app/services/mass_cg_service.py:78` | `aggregate_weight_items` | 🟢 |
| `app/services/mass_cg_service.py:105-128` | `_get_aeroplane`, `get_effective_assumption_value` | 🟢 |
| `app/services/mass_cg_service.py:224-282` | `get_cg_comparison`, `get_s_ref_for_aeroplane`, `get_design_metrics_for_aeroplane` | 🟢 |
| `app/api/v2/endpoints/aeroplane/mass_cg.py` | 2 routes, `_raise_http`, `_call` | 🟢 |
| `app/schemas/mass_cg.py` | `DesignMetricsRequest/Response`, `CGComparisonResponse` | 🟢 |
| `app/schemas/mass_cg.py:8-23` | `RecommendedCGRequest/Response` | 🔴 dead |
</content>
