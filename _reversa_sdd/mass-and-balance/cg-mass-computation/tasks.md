# cg-mass-computation — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `weight_items` rows available — see
      [`../weight-items/tasks.md`](../weight-items/tasks.md) T-01…T-04. This use
      case reads them; it never writes them.
- [ ] `design_assumptions` table with `parameter_name`, `estimate_value`,
      `calculated_value`, `active_source` — module `mission-and-sizing`.
- [ ] `app/core/exceptions.py` with `NotFoundError`, `ValidationError`,
      `InternalError`.
- [ ] `analysis_service.get_aeroplane_schema_or_raise` and
      `model_schema_converters.aeroplane_schema_to_asb_airplane_async` — module
      `aero-analysis`. May be stubbed for everything except T-06/T-07.
- [ ] AeroSandbox installed for the `design_metrics` path only; every other task
      must pass without it (ADR 0017).

## Tasks

- [ ] **T-01 — Constants and the input TypedDict.**
  `GRAVITY = 9.81`, `CG_TOLERANCE_M = 0.01`,
  `WeightItemData = TypedDict{mass_kg, x_m, y_m, z_m}`.
  - Legacy origin: `app/services/mass_cg_service.py:20-28`
  - Definition of done: the constants are module-level and referenced by name,
    never inlined. Record in the gap list that `9.81` differs from the
    `9.80665` used by `endurance_service` and the powertrain services.
  - Confidence: 🟢

- [ ] **T-02 — `aggregate_weight_items` (pure).**
  Empty input ⇒ four `None`s; `total_mass ≤ 0` ⇒ four `None`s; otherwise
  `cg_k = Σ(mᵢ·kᵢ)/m_tot` for x, y and z. **No rounding.**
  - Legacy origin: `app/services/mass_cg_service.py:78-97`
  - Definition of done: a 0.4/0.6 kg fixture reproduces `(1.0, 0.16, 0.0, 0.0)`
    to full float precision; `[]`, an all-zero-mass list and a negative-total
    list each return four `None`s. A test must fail if any of them returns `0.0`.
  - Confidence: 🟢

- [ ] **T-03 — `compute_recommended_cg` (pure).**
  `np_x − target_static_margin · mac`.
  - Legacy origin: `app/services/mass_cg_service.py:36-38`
  - Definition of done: one unit test (`0.5, 0.2, 0.12 → 0.476`). **Do not wire
    it to a route** — the legacy has none; record the triplication with
    `loading_scenario_service` and `assumption_compute_service` as a gap.
  - Confidence: 🟢

- [ ] **T-04 — `compute_design_metrics` (pure) with five input guards.**
  Reject `mass_kg`, `s_ref`, `cl_max`, `rho`, `velocity` at `≤ 0`, each with its
  own `"<field> must be positive"` message, **before** any arithmetic; then
  evaluate W, W/S, V_stall, q, CL_req and CL_margin per
  [`design.md`](design.md) §F6.
  - Legacy origin: `app/services/mass_cg_service.py:41-75`
  - Definition of done: five parametrised rejection tests asserting the exact
    message; one numeric test reproducing all four derived values to 1e-9 with
    `GRAVITY = 9.81`. Assert the response has **no** nullable field.
  - Confidence: 🟢

- [ ] **T-05 — `get_effective_assumption_value` (local resolver).**
  `calculated_value` when `active_source == "CALCULATED"` **and** it is not
  `None`; otherwise `estimate_value`. A missing row raises
  `NotFoundError(entity="DesignAssumption", resource_id=param_name)`.
  - Legacy origin: `app/services/mass_cg_service.py:112-128`
  - Definition of done: a table-driven test over the three
    (`active_source`, `calculated_value`) combinations plus the missing-row
    case. A test must fail if a `PARAMETER_DEFAULTS` fallback is introduced —
    that is the *other* resolver's contract.
  - Confidence: 🟢

- [ ] **T-06 — `get_s_ref_for_aeroplane`.**
  Resolve the schema, build the ASB airplane (lazy imports), read
  `getattr(airplane, "s_ref", 0.0) or 0.0`; `≤ 0` ⇒ `ValidationError("Wing
  reference area (s_ref) is zero or negative — add wings first")`; a build
  failure ⇒ logged + `InternalError("Could not compute wing reference area: …")`.
  - Legacy origin: `app/services/mass_cg_service.py:252-268`
  - Definition of done: three tests — a normal wing returns its area; a wingless
    aeroplane raises `ValidationError` with the exact remediation sentence; a
    converter patched to raise yields `InternalError`.
  - Confidence: 🟢

- [ ] **T-07 — `get_design_metrics_for_aeroplane` with the lazy ASB import.**
  `import aerosandbox as asb` **inside** the function; resolve `mass` and
  `cl_max` through T-05, `s_ref` through T-06, `ρ` from
  `asb.Atmosphere(altitude=…).density()`; delegate to T-04.
  - Legacy origin: `app/services/mass_cg_service.py:271-282`
  - Definition of done: an altitude of 1000 m yields a lower ρ and a higher
    stall speed than 0 m; importing the module with `aerosandbox` removed from
    `sys.modules` succeeds and every other function still works.
  - Confidence: 🟢

- [ ] **T-08 — `get_cg_comparison`.**
  Resolve the aeroplane, resolve `cg_x` through T-05, aggregate the inventory
  through T-02, derive `delta_x = design − component` and
  `within_tolerance = |delta_x| < CG_TOLERANCE_M` (**strict**), and return all
  four component fields as `None` together when there is no aggregate.
  - Legacy origin: `app/services/mass_cg_service.py:224-249`
  - Definition of done: four tests — inside, outside, exactly `0.01` (must be
    `False`), and the empty inventory (`delta_x` and `within_tolerance` both
    `null`, `design_cg_x` populated).
  - Confidence: 🟢

- [ ] **T-09 — The two routes and their error mapping.**
  `POST /aeroplanes/{aeroplane_id}/design_metrics` (200,
  `operation_id=compute_design_metrics`) and
  `GET /aeroplanes/{aeroplane_id}/cg_comparison` (200,
  `operation_id=get_cg_comparison`); `_raise_http` maps
  `NotFoundError→404`, `ValidationError`/`ValidationDomainError→422`,
  `ConflictError→409`, else 500; `_call` logs the catch-all with
  `exc_info=True` before raising `500 {"detail": "Unexpected error: …"}`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/mass_cg.py`
  - Definition of done: contract tests for 200 / 404 / 422 on both routes, plus
    an assertion that the error body is `{"detail": …}` with no `error` object.
  - Confidence: 🟢

- [ ] **T-10 — `DesignMetricsRequest` bounds.**
  `velocity: float = 15` with `gt=0`; `altitude: float = 0` with `ge=0`.
  - Legacy origin: `app/schemas/mass_cg.py`
  - Definition of done: `velocity = 0` is rejected by Pydantic (422) *before*
    T-04's guard is reached; `altitude = -100` is likewise 422.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Aggregation matrix:** empty · single · multi-item three-axis ·
      all-zero mass · negative total. Assert `None`, never `0.0`.
- [ ] **TT-02 — Aggregation precision:** an asymmetric fixture reproduces the
      mass-weighted CG to 1e-12 (the function does not round).
- [ ] **TT-03 — Resolver matrix:** CALCULATED+value · CALCULATED+`null` ·
      ESTIMATE · missing row (raises).
- [ ] **TT-04 — Design-metric rejection:** five parametrised 422s with exact
      messages.
- [ ] **TT-05 — Design-metric numerics:** all four outputs against hand-computed
      values; a second case at a different `cl_max` to catch a swapped operand.
- [ ] **TT-06 — CL margin sign:** a velocity below stall yields a negative
      `cl_margin`, and the call still succeeds (it is a *report*, not an error).
- [ ] **TT-07 — Altitude effect:** ρ falls and `stall_speed_ms` rises between
      0 m and 1000 m.
- [ ] **TT-08 — `s_ref` failures:** wingless (422 + remediation) and converter
      failure (500).
- [ ] **TT-09 — CG comparison matrix:** inside · outside · exactly at tolerance
      (`false`) · empty inventory (`null` verdict) · missing `cg_x` row (404).
- [ ] **TT-10 — Δx sign:** a design CG aft of the component CG yields a
      **positive** `delta_x` (pins the convention the UI depends on).
- [ ] **TT-11 — Import guard:** importing `mass_cg_service` must not import
      `aerosandbox`, `design_assumptions_service` or `analysis_service`.
- [ ] **TT-12 — `compute_recommended_cg`** matches
      `loading_scenario_service.compute_stability_envelope` for the same inputs
      — a cross-implementation consistency test that will fail if the two ever
      diverge. 🟡 documents the triplication rather than fixing it.
- [ ] **TT-13 — Error-envelope guard:** both routes return `{"detail": …}` on
      every error, never `{"error": {…}}`.

## Data Migration Tasks

None. This use case persists nothing — every value it produces is derived per
request and discarded after serialisation. 🟢

## Suggested Order

1. **T-01 → T-02 → T-03 → T-04** first: constants and the three pure functions.
   They carry the whole use case's arithmetic and need neither a database nor
   HTTP, so they are the cheapest place to pin the formulas.
2. **T-05** next — every DB-aware function below depends on it, and it is a
   pure-logic function with a trivial fixture.
3. **T-08** after T-02 + T-05: the CG comparison is just those two composed plus
   the tolerance rule. It needs no AeroSandbox and is fully testable.
4. **T-06 → T-07** last among the services: they are the only tasks that require
   the converter stack and AeroSandbox, and T-07 is a four-line composition once
   T-04, T-05 and T-06 exist.
5. **T-10 → T-09** to close: the request bounds, then the routes.

T-03 has no downstream dependency at all and can be done at any point.

## Pending Gaps (🔴)

- **Should the CG comparison include the component tree?** Today only
  `weight_items` carry positions, so an aircraft built entirely in the tree has
  a mass but a `null` CG — and the response gives no reason.
- **Which effective-value resolver is canonical** — the raising one here or the
  `PARAMETER_DEFAULTS`-defaulting one in `design_assumptions_service`?
- **Should `compute_recommended_cg` become the single implementation** of
  `x_np − SM·MAC`, and should the dead `RecommendedCGRequest` /
  `RecommendedCGResponse` schemas be deleted or wired up?
- **Should `s_ref` come from `assumption_computation_context["s_ref_m2"]`**
  instead of a fresh ASB build on every `design_metrics` call? Nothing currently
  asserts the two agree.
- **One gravity constant or two?** `9.81` here versus `9.80665` in the
  powertrain and endurance stack.
- **Should `cg_y` / `cg_z` reach a consumer**, or be dropped from the response?
- **Should a missing assumption row be distinguishable from a missing
  aeroplane** in the 404 body?
- **Should the routers use `NonFiniteSafeJSONResponse`** as the analysis router
  does (ADR 0012), even though the current guards make NaN unreachable?
</content>
