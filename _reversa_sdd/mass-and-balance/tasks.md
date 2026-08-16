# mass-and-balance — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Use-case task lists: [`weight-items`](weight-items/tasks.md) ·
> [`cg-mass-computation`](cg-mass-computation/tasks.md) ·
> [`component-tree-mass-sync`](component-tree-mass-sync/tasks.md).

## Prerequisites

- [ ] `aeroplanes` table with the public `uuid` column, and a resolver that
      raises `NotFoundError(entity="Aeroplane")`.
- [ ] `design_assumptions` table plus `design_assumptions_service`
      (`update_calculated_value`, `get_effective_assumption`,
      `PARAMETER_DEFAULTS` with `mass = 1.5`) — module `mission-and-sizing`.
- [ ] `invalidation_service.mark_ops_dirty` and the `event_bus` with the
      `AssumptionChanged` event type.
- [ ] `component_tree_service.get_aircraft_total_weight_kg` — module
      `aeroplane-core`. May be stubbed: the sync must work when it raises.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009).
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`,
      `ValidationDomainError`, `ConflictError`, `InternalError`,
      `ServiceException`).
- [ ] AeroSandbox available on the platform **or** the `design_metrics` route
      accepted as degraded (ADR 0017) — every other route must work without it.

## Tasks

- [ ] **T-01 — `weight_items` table and ORM relationship.**
  Columns: `aeroplane_id` (int FK → `aeroplanes.id`, `ON DELETE CASCADE`,
  indexed), `name`, `mass_kg`, `x_m`, `y_m`, `z_m` (default `0.0`),
  `description`, `category` (default `"other"`). Relationship
  `AeroplaneModel.weight_items` with `cascade="all, delete-orphan"` and
  `order_by=id`.
  - Legacy origin: `app/models/aeroplanemodel.py:798`
  - Definition of done: deleting an aeroplane removes its weight items; the list
    endpoint returns them in id order.
  - Confidence: 🟢

- [ ] **T-02 — The write/read schemas and the category set.**
  `WeightItemWrite` (`name` min 1, `mass_kg ≥ 0`, three positions defaulting to
  `0.0`, `description`, `category`), `WeightItemRead = Write + id`,
  `WeightSummary(items, total_mass_kg, cg_x_m, cg_y_m, cg_z_m)`.
  `WEIGHT_CATEGORIES = {electronics, battery, structural, payload, other}`.
  - Legacy origin: `app/schemas/weight_item.py:8`
  - Definition of done: `mass_kg = -1` and `name = ""` are both 422; an unknown
    category is 422; the DB column stays a plain `String` (documented, not
    fixed — see the pending gaps).
  - Confidence: 🟢

- [ ] **T-03 — `aggregate_weight_items` (pure).**
  Takes `Sequence[WeightItemData]` dicts — **not** ORM rows. Empty input or
  `m_tot ≤ 0` returns `(None, None, None, None)`; otherwise
  `cg_k = Σ(mᵢ·kᵢ)/m_tot` for x, y and z. No rounding.
  - Legacy origin: `app/services/mass_cg_service.py:78-97`
  - Definition of done: a 2-item fixture reproduces the CG to full float
    precision; an empty list and an all-zero-mass list both return four `None`s.
  - Confidence: 🟢

- [ ] **T-04 — Weight-item CRUD service.**
  Five functions, each resolving the aeroplane first and scoping the item query
  by `aeroplane_id AND id`. `create`/`update` `flush()` + `refresh()`;
  `SQLAlchemyError` is re-raised as `InternalError`; `NotFoundError` passes
  through untouched.
  - Legacy origin: `app/services/weight_items_service.py:67-137`
  - Definition of done: an item id from another aeroplane returns 404, not the
    row; a PUT with an omitted `x_m` resets it to `0.0` (full replacement).
  - Confidence: 🟢

- [ ] **T-05 — `list_weight_items` inline summary with 6-dp rounding.**
  Recompute total and the three CGs over the mapped read objects, round each to
  6 decimals, and return `cg_* = None` when `total ≤ 0` while `total_mass_kg`
  is `round(total, 6)` — i.e. `0`, not `None`.
  - Legacy origin: `app/services/weight_items_service.py:36-54`
  - Definition of done: an empty inventory yields `total_mass_kg = 0` **and**
    three `null` CGs; a fixture whose exact CG is `0.1234565` rounds as the
    legacy does.
  - Confidence: 🟢 · 🟡 the duplication with T-03 is deliberate legacy
    behaviour; reproduce it, then record the divergence risk.

- [ ] **T-06 — `_try_sync_assumptions` best-effort wrapper.**
  Function-local import of `mass_cg_service.sync_weight_items_to_assumptions`;
  catch `NotFoundError` and `SQLAlchemyError` only, log a warning, continue.
  Call it at the end of create, update and delete — never in the read paths.
  - Legacy origin: `app/services/weight_items_service.py:57-64, 74, 111, 132`
  - Definition of done: with the sync patched to raise `SQLAlchemyError`, all
    three write routes still return their success status and the row is
    persisted; the warning is logged. A module-level import must not
    reintroduce the `weight_items_service ↔ mass_cg_service` cycle.
  - Confidence: 🟢

- [ ] **T-07 — `sync_weight_items_to_assumptions` (producer A).**
  Five steps per BR-MB2: resolve → probe for the `"mass"` row (absent ⇒
  `return`) → aggregate (dropping all three CGs) → `update_calculated_value(…,
  source="weight_items" if total is not None else None,
  auto_switch_source=True)` → `mark_ops_dirty` + publish
  `AssumptionChanged(mass)`.
  - Legacy origin: `app/services/mass_cg_service.py:174-221`
  - Definition of done: a test asserts the `cg_x` assumption row is **unchanged**
    after a sync (ADR 0011); a second test asserts the no-op path creates no
    rows on an unseeded aircraft.
  - Confidence: 🟢

- [ ] **T-08 — `sync_component_tree_to_mass` (producer B).**
  Identical five steps, aggregating via
  `component_tree_service.get_aircraft_total_weight_kg` (function-local import)
  and labelling the source `"component_tree"`.
  - Legacy origin: `app/services/mass_cg_service.py:131-171`
  - Definition of done: an empty tree (aggregate `None`) writes
    `calculated_value = None` **and** `calculated_source = None`; a 350 g tree
    writes `0.35`.
  - Confidence: 🟢

- [ ] **T-09 — `get_effective_assumption_value` (local resolver).**
  `calculated_value` when `active_source == "CALCULATED"` and it is not `None`,
  otherwise `estimate_value`; a missing row raises
  `NotFoundError(entity="DesignAssumption", resource_id=param_name)`.
  - Legacy origin: `app/services/mass_cg_service.py:112-128`
  - Definition of done: a table-driven test over
    (`active_source`, `calculated_value`) → expected value; the missing-row case
    raises rather than falling back. **Record the divergence** from
    `design_assumptions_service.get_effective_assumption` in the gap list.
  - Confidence: 🟢

- [ ] **T-10 — `get_cg_comparison`.**
  Resolve the design `cg_x`, aggregate the inventory, and derive
  `delta_x = design − component` with `within_tolerance = |delta_x| <
  CG_TOLERANCE_M` (`0.01`). All four component fields plus `delta_x` and
  `within_tolerance` are `None` when there is no aggregate.
  - Legacy origin: `app/services/mass_cg_service.py:224-249`
  - Definition of done: three tests — inside tolerance, outside tolerance, and
    the empty-inventory case where the verdict is `null` (**not** `false`).
  - Confidence: 🟢

- [ ] **T-11 — `compute_design_metrics` (pure) with input rejection.**
  Reject `mass_kg`, `s_ref`, `cl_max`, `rho`, `velocity` at `≤ 0` with a
  per-input `ValidationError` message, then evaluate BR-MB10 with
  `GRAVITY = 9.81`.
  - Legacy origin: `app/services/mass_cg_service.py:41-75`
  - Definition of done: five parametrised rejection tests, each asserting the
    exact message; one numeric test reproducing all four derived values to
    within 1e-9.
  - Confidence: 🟢

- [ ] **T-12 — `get_s_ref_for_aeroplane`.**
  Resolve the aeroplane schema, convert to an ASB airplane, read `s_ref`, and
  raise `ValidationError("… add wings first")` for `s_ref ≤ 0`. A conversion
  failure is logged and re-raised as `InternalError`.
  - Legacy origin: `app/services/mass_cg_service.py:252-268`
  - Definition of done: a wingless aeroplane returns 422 with the remediation
    sentence; a converter patched to raise returns 500.
  - Confidence: 🟢

- [ ] **T-13 — `get_design_metrics_for_aeroplane` with the lazy ASB import.**
  `import aerosandbox as asb` **inside** the function; `ρ =
  asb.Atmosphere(altitude).density()`; `mass` and `cl_max` from T-09.
  - Legacy origin: `app/services/mass_cg_service.py:271-282`
  - Definition of done: importing `mass_cg_service` on a machine without ASB
    succeeds and every non-metrics route still works — verified by an import
    test that stubs `aerosandbox` out of `sys.modules`.
  - Confidence: 🟢

- [ ] **T-14 — `compute_recommended_cg` (pure).**
  `np_x − target_static_margin · mac`.
  - Legacy origin: `app/services/mass_cg_service.py:36-38`
  - Definition of done: one unit test. **Do not wire it into a route** — the
    legacy has none; record the duplication with
    `loading_scenario_service.compute_stability_envelope` and
    `assumption_compute_service` as a gap.
  - Confidence: 🟢

- [ ] **T-15 — The five weight-item routes.**
  Paths, status codes (201 create, 204 delete) and the
  `_raise_http` / `_call` error mapping exactly as in
  [`contracts.md`](contracts.md).
  - Legacy origin: `app/api/v2/endpoints/aeroplane/weight_items.py`
  - Definition of done: contract tests for each status code, including the
    204-with-empty-body case and the cross-aeroplane 404.
  - Confidence: 🟢

- [ ] **T-16 — The two mass/CG routes.**
  `POST …/design_metrics` (200) and `GET …/cg_comparison` (200), same error
  mapping, with `exc_info=True` on the `mass_cg` catch-all log line.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/mass_cg.py`
  - Definition of done: contract tests for 200 / 404 / 422; a test asserting
    the response body shape is `{"detail": …}` and **not** `{"error": {…}}`.
  - Confidence: 🟢

- [ ] **T-17 — Wire the tree-side sync call site.**
  `component_tree_service._sync_aircraft_mass` must call
  `sync_component_tree_to_mass` from create, update, delete and move, wrapped in
  a bare `except Exception`.
  - Legacy origin: `app/services/component_tree_service.py:362-378`
  - Definition of done: each of the four tree write paths triggers exactly one
    sync attempt (spy) and survives a raising sync.
  - Confidence: 🟢 · owned by `aeroplane-core`; verify the wiring from this side
    too, because this module is where the failure becomes visible.

## Test Tasks

- [ ] **TT-01 — Aggregation matrix:** empty · all-zero mass · single item ·
      multi-item three-axis CG · negative total (⇒ four `None`s).
- [ ] **TT-02 — Summary rounding:** the route rounds to 6 dp and reports
      `total_mass_kg = 0` with `null` CGs for an empty inventory.
- [ ] **TT-03 — CRUD happy paths + the four failure modes:** unknown aeroplane
      (404), unknown item (404), cross-aeroplane item (404), invalid body (422).
- [ ] **TT-04 — Sync writes the calculated side only:** `estimate_value` and
      `cg_x` are byte-identical before and after (guards ADR 0011).
- [ ] **TT-05 — Auto-switch fires once:** ESTIMATE → CALCULATED on the first
      non-empty sync; a manual switch back to ESTIMATE survives the next sync.
- [ ] **TT-06 — Emptying clears:** deleting the last item sets both
      `calculated_value` and `calculated_source` to `None`.
- [ ] **TT-07 — Unseeded no-op:** a sync against an aircraft with no `"mass"`
      row creates nothing and raises nothing.
- [ ] **TT-08 — Best-effort:** patch the sync to raise; create, update and
      delete all still succeed and log a warning.
- [ ] **TT-09 — Events:** exactly one `AssumptionChanged(mass)` and one
      `mark_ops_dirty` per successful sync, including the `None`-writing sync.
- [ ] **TT-10 — Producer collision (characterisation):** sync weight items, then
      the tree, then the weight items again; assert `calculated_source` follows
      the last writer. This test **documents** BR-MB4 rather than endorsing it.
- [ ] **TT-11 — CG comparison:** inside · outside · exactly at 0.01 m (must be
      `false`, the comparison is strict `<`) · empty inventory (`null` verdict).
- [ ] **TT-12 — Design-metric rejection matrix:** five parametrised 422s with
      their exact messages, plus the wingless 422.
- [ ] **TT-13 — Design-metric numerics:** wing loading, stall speed, required CL
      and CL margin against hand-computed values with `GRAVITY = 9.81`.
- [ ] **TT-14 — Import-cycle guard:** importing `weight_items_service` must not
      import `mass_cg_service`, and importing `mass_cg_service` must not import
      `design_assumptions_service`, `invalidation_service` or `aerosandbox`.
- [ ] **TT-15 — Error-envelope guard:** every 4xx/5xx from these seven routes has
      a top-level `detail` string and no `error` object.

## Data Migration Tasks

- [ ] **TM-01 — Backfill nothing.** The module has no derived persisted state:
      totals, CGs, deltas and metrics are computed per request. The only rows
      are the user's `weight_items`. 🟢
- [ ] **TM-02 — If `category` is to become a real constraint**, first survey the
      existing distinct values (the column is unconstrained today) before adding
      a CHECK or enum; a direct-SQL or import-written value outside the five
      would break the read path. 🟢 decided (`Q-MB-1`): `weight_items` is retired; the read path moves to the component tree.

## Suggested Order

1. **T-01 → T-02** — the table and the schemas gate everything else.
2. **T-03, T-11, T-14** next: all three are pure functions, testable with no DB
   and no HTTP. They carry most of the module's actual arithmetic.
3. **T-04, T-05, T-15** — the inventory CRUD and its routes; this is a complete,
   shippable slice on its own (see [`weight-items`](weight-items/tasks.md)).
4. **T-09** before T-07/T-08/T-10, since all three resolve assumptions through
   it.
5. **T-06 → T-07 → T-08** — the sync chain. T-07 and T-08 are independent of
   each other and can be built in parallel; T-06 is what makes them safe.
6. **T-10, T-12, T-13, T-16** last — the read-only comparison and metrics
   surfaces sit on top of everything above. T-12/T-13 are the only tasks that
   need AeroSandbox.
7. **T-17** whenever `aeroplane-core`'s component tree exists; it is the one
   task that reaches out of the module.

## Pending Gaps (🔴)

- **Which mass producer wins?** Weight items and the component tree overwrite
  one another's `calculated_value` last-write-wins. Should the aircraft pick a
  producer explicitly, should the tree take precedence once it is non-empty, or
  should the two be merged (the weight inventory folded into the tree)?
- **Should `weight_items` reference COTS components?** Without a `component_id`
  the same battery can be counted in both producers with nothing detecting it.
- **Which effective-value resolver is canonical?**
  `mass_cg_service.get_effective_assumption_value` raises on a missing row;
  `design_assumptions_service.get_effective_assumption` falls back to
  `PARAMETER_DEFAULTS`. Two aircraft in one database behave differently
  depending on the caller.
- **One gravity constant or two?** `9.81` here versus `9.80665` in the
  powertrain and endurance stack.
- **Should `cg_y` / `cg_z` reach a consumer?** They are computed and published
  on two schemas and read by nothing — a laterally unbalanced aircraft produces
  no signal.
- **Should `compute_recommended_cg` become the single implementation** of
  `x_np − SM·MAC`, replacing the copies in `loading_scenario_service` and
  `assumption_compute_service`? And should the dead `RecommendedCGRequest` /
  `RecommendedCGResponse` schemas be deleted or wired to a route?
- **Should a persistently failing sync be surfaced?** Today it only logs, which
  contradicts ADR 0012's "design warnings, not silent fallbacks".
- **Should `category` be constrained in the database**, and if so, what happens
  to values already stored outside the five-item set?
- **Should this module adopt the `{"error": {code, message, details}}`
  envelope** used by `aeroplane-core`, and should the raw exception text stop
  being interpolated into 500 bodies?
</content>
