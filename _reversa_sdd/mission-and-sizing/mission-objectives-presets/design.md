# mission-objectives-presets — Technical Design

> Use-case design, nested under the module
> [`mission-and-sizing`](../design.md).
> Focuses on HOW this use case is built, read from the legacy code.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Companion documents: [`requirements.md`](requirements.md),
> [`tasks.md`](tasks.md), [`../contracts.md`](../contracts.md) §B.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_default_objective` | `()` | `MissionObjective` | a **new instance per call** — never a shared singleton 🟢 |
| `get_mission_objective` | `(db, aeroplane_id: int)` | `MissionObjective` | returns the default when no row exists; persists nothing 🟢 |
| `upsert_mission_objective` | `(db, aeroplane_id: int, payload)` | `MissionObjective` | applies preset estimates on a `mission_type` change 🟢 |
| `_apply_preset_estimates` | `(db, aeroplane_id: int, mission_type: str)` | `None` | 🟢 routes through `update_assumption` (`Q-MS-10`); writes `estimate_value` only; silent on an unknown id 🟢 / 🔴 |
| `list_mission_presets` | `(db)` | `list[MissionPreset]` | converts `axis_ranges` lists → tuples 🟢 |
| `seed_mission_presets` | `(db)` | `None` | idempotent by id 🟢 |
| `compute_mission_kpis` | `(db, aeroplane_id: int, active_mission_ids: list[str])` | `MissionKpiSet` | closed-form; no solver 🟢 |
| `_normalise_score` | `(value, lo, hi)` | `float` | clipped to `[0,1]`; `hi <= lo` ⇒ `0.0` 🟢 |
| `_ctx_get` | `(ctx, key)` | `float \| None` | non-numeric, zero and negative all read as absent 🟢 |
| `_resolve_polar_inputs` | `(ctx)` | `(ld_max, cd0, e, ar)` | the gh-681 provenance chain 🟢 |
| `_objective_target_scores` | `(objective, axis_ranges)` | `dict[AxisName, float]` | the gh-767 Soll polygon 🟢 |
| `_hash_context` | `(ctx)` | `str` (64 hex) | emitted, never consumed 🟡 |

HTTP surface: see [`../contracts.md`](../contracts.md) §B — four routes.

## Main Flow

```
1. GET /aeroplanes/{uuid}/mission-objectives
       row missing → _default_objective()          (NOT persisted)
       row present → MissionObjective.model_validate(row, from_attributes=True)

2. PUT /aeroplanes/{uuid}/mission-objectives
       old_mission_type = row.mission_type if row else None
       row = row or MissionObjectiveModel(aeroplane_id=…)     ← db.add
       for field, value in payload.model_dump().items():  setattr(row, field, value)
       db.flush()
       if old_mission_type != payload.mission_type:
           _apply_preset_estimates(db, aeroplane_id, payload.mission_type)
       db.refresh(row);  return the schema

3. _apply_preset_estimates
       preset = mission_presets[mission_type]  or  REJECT           ← 🟢 Q-MS-10
       for param_name, value in preset.suggested_estimates.items():
           row = design_assumptions[(aeroplane_id, param_name)]
                 or DesignAssumptionModel(aeroplane_id, parameter_name)  ← db.add
           row.estimate_value = value          ← ONLY this field
       db.flush()

4. GET /aeroplanes/{uuid}/mission-kpis?missions=a&missions=b
       ctx        = aeroplane.assumption_computation_context or {}
       objective  = get_mission_objective(...)
       presets    = {p.id: p for p in list_mission_presets(db)}
       ids        = missions or [objective.mission_type]
       primary    = presets.get(ids[0]) or presets.get("trainer") or RAISE
       rng        = primary.axis_ranges
       mass       = ctx["mass_kg"] (>0)  else  aeroplane.total_mass_kg  else None
       ist        = the seven _kpi_* calculators, each with rng[axis]
       targets    = for each resolvable id:
                      id == objective.mission_type
                        ? _objective_target_scores(objective, preset.axis_ranges)   (gh-767)
                        : preset.target_polygon                                     (static)
       return MissionKpiSet(…, active_mission_id=ids[0],
                            computed_at=utcnow().isoformat(),
                            context_hash=sha256(json(ctx, sort_keys=True)))
```

## The nine presets 🟢

`suggested_estimates` — the five values written into
`design_assumptions.estimate_value` on a mission change:

| id | `g_limit` | `target_static_margin` | `cl_max` | `power_to_weight` | `prop_efficiency` |
|---|---|---|---|---|---|
| `trainer` | 3.0 | 0.15 | 1.4 | **0.5** 🟢 re-authored to W/kg (`Q-MS-1`) | 0.70 |
| `sport` | 5.0 | 0.10 | 1.3 | **0.7** 🟢 re-authored to W/kg (`Q-MS-1`) | 0.70 |
| `sailplane` | 5.3 | 0.10 | 1.3 | 0.0 | 0.00 |
| `wing_racer` | 10.0 | 0.05 | 1.0 | **1.0** 🟢 re-authored to W/kg (`Q-MS-1`) | 0.70 |
| `acro_3d` | 8.0 | **0.0** | 1.1 | **1.4** 🔴 | 0.70 |
| `stol_bush` | 4.0 | 0.15 | 2.0 | **0.8** 🔴 | 0.70 |
| `slope_soarer` | 6.0 | 0.08 | 1.1 | 0.0 | 0.00 |
| `motor_glider` | 5.3 | 0.10 | 1.4 | **100.0** | 0.65 |
| `flying_wing` | 5.0 | 0.075 | 1.0 | **100.0** | 0.65 |

🔴 The `power_to_weight` column is dimensionally split (BR-MS34): the assumption
catalogue types it **W/kg** with a default of `220.0`, `motor_glider` and
`flying_wing` (gh-580) write real W/kg, and the other seven write a
dimensionless T/W-shaped number. The regression tests assert
`power_to_weight == 0.0` for `sailplane` / `slope_soarer` and `== 100.0` for
`motor_glider`, with the comment *"100 W/kg covers self-launch climb (80–150
range)"* — so W/kg is the intended unit and seven presets are wrong by roughly
two orders of magnitude.
🟢 `acro_3d` deliberately sets `target_static_margin = 0.0` — neutral stability
is the 3D mission, not an omission. `motor_glider` carries an in-code caveat
that `prop_efficiency = 0.65` reflects the **climb** segment and that
`g_limit = 5.3` cites CS-22.337's utility-category ultimate factor.

`target_polygon` and `axis_ranges` differ per preset. `trainer` as the
exemplar 🟢:

```
target_polygon  stall_safety 1.0 · glide 0.4 · climb 0.3 · cruise 0.3
                maneuver 0.3 · wing_loading 0.3 · field_friendliness 0.9
axis_ranges     stall_safety (1.3, 2.5) · glide (5, 18) · climb (5, 25)
                cruise (10, 25) · maneuver (2, 5) · wing_loading (20, 80)
                field_friendliness (3, 100)
```

🟡 `wing_loading` ranges are given in the 20–120 band while the Ist axis
computes `m·g/S_ref` in **N/m²** — a 412 N/m² objective default would clip to
1.0 on every preset. Either the ranges are in a different unit (g/dm²-derived)
or the objective default is out of family. The code contains no statement
either way.

Storage note 🟢: `axis_ranges` is written as `{axis: [min, max]}` (JSON lists)
and read back as tuples (`list_mission_presets` converts with
`tuple(v)`), because the Pydantic schema types it
`dict[AxisName, tuple[float, float]]`.

## The seven Ist axes 🟢

| Axis | Formula (as reported in `MissionAxisKpi.formula`) | Inputs | Unit |
|---|---|---|---|
| `stall_safety` | `V_cruise / V_s1` | `v_cruise_mps`, `v_s1_mps` | `-` |
| `glide` | `(L/D)_max = 0.5 · √(π · e · AR / C_D0)` | empirical `ld_max` preferred | `-` |
| `climb` | `(C_L^1.5 / C_D)_max = (3·π·e·AR)^0.75 / (4 · C_D0^0.25)` | `cd0`, `e`, `ar` | `-` |
| `cruise` | `V_cruise (from ComputationContext)` | `v_cruise_mps` | m/s |
| `maneuver` | `n_max from V-n diagram (load factor)` | `flight_envelope_n_max` | g |
| `wing_loading` | `W/S = m·g / S_ref` | mass, `s_ref_m2`, `g = 9.81` | N/m² |
| `field_friendliness` | `max(s_TO_50ft, s_LDG_50ft); score = target / effective` | `field_length_service` | m |

The climb closed form is derived in a code comment 🟢: for
`CD = CD0 + CL²/(π·e·AR)`, setting `d(CL^1.5/CD)/dCL = 0` gives `1.5·CD =
2·k·CL²`, hence `CL*² = 3·π·e·AR·CD0` and `CD* = 4·CD0`.

### The gh-681 provenance chain (`_resolve_polar_inputs`) 🟢

```
ar   ← ctx["aspect_ratio"];  absent or ≤ 0  ⇒  (None, None, None, None)  — hard stop
ld   ← polar_by_config.clean.ld_max          (empirical max CL/CD from the sweep, gh-636)
        non-numeric or ≤ 0 ⇒ None
cd0  ← polar_by_config.clean.cd0  →  ctx["cd0"]     (always-written stability-run cd0)
e    ← polar_by_config.clean.e_oswald → ctx["e_oswald"]  (AB-Trefftz, gh-636)
```

The two-step fallback exists so the axes **survive a rejected parabolic fit**:
the clean polar's `cd0` / `e_oswald` are `None` when the fit gates rejected it,
but the top-level context keys are populated independently. `glide` prefers the
measured `ld_max` and only falls back to the formula. 🟢

### Missing-axis semantics 🟢

`_missing(axis, lo, hi, formula, warning=None)` returns
`value = unit = score_0_1 = None` with `provenance = "missing"` and the range
still populated, so the radar knows where the gap is. `_ctx_get` returns `None`
for absent keys, non-numerics **and** any value `≤ 0` — none of the consumed
quantities is physically non-positive, so a zero is a missing reading, not a
measurement.
🟡 `_normalise_score` returns `0.0` for a degenerate range (`hi <= lo`) rather
than `None`, with the stated rationale that *"there is no defensible
interpretation of where in the range the value sits"* — the one place an
unknown answer is rendered as a bad one.

### `field_friendliness` — the only axis that leaves the module 🟢

```
compute_field_lengths_for_aeroplane is imported at MODULE level inside a
try/except ImportError, so the symbol exists for both runtime and
unittest.mock.patch("…mission_kpi_service.compute_field_lengths_for_aeroplane")
    None                    → ("Field-length service unavailable on this platform")
    ImportError at call     → the same message (lazy aerosandbox import)
    ServiceException        → provenance "missing", warning = exc.message
                              (user-actionable: missing t_static_N, s_ref_m2, …)
    any other exception     → PROPAGATES — it is a bug, not a user condition

eff   = max(s_to_50ft_m, s_ldg_50ft_m);   eff <= 0 → missing
score = clip(target_field_length_m / eff, 0, 1)     ← shorter field is better
```

Passing `db` is *strongly preferred* so the `MissionObjective` lookup stays in
the caller's session — required by tests on a transient SQLite database. 🟢

### The Soll polygon (gh-767) 🟢

```
for mid in active_mission_ids:
    preset = presets.get(mid)  or  continue          ← unknown overlays vanish
    scores = _objective_target_scores(objective, preset.axis_ranges)
                if mid == objective.mission_type
             else preset.target_polygon

_objective_target_scores maps the user's six numeric targets through the SAME
_normalise_score and the SAME axis_ranges as the matching Ist axis:
    stall_safety  ← target_stall_safety
    glide         ← target_glide_ld
    climb         ← target_climb_energy
    cruise        ← target_cruise_mps
    maneuver      ← target_maneuver_n
    wing_loading  ← target_wing_loading_n_m2
    field_friendliness ← 1.0                       ← by construction, see below
```

`field_friendliness` is excluded from normalisation because its **Ist** axis is
already an achievement ratio (`target / effective`), not a physical value on the
range — meeting the declared target is by definition full score. 🟢

## Alternative Flows

- **No mission-objective row.** `get_mission_objective` returns a fresh
  `_default_objective()`; nothing is written. The KPI service therefore always
  has an objective, even for an untouched aeroplane. 🟢
- **Unknown `mission_type` on upsert.** `_apply_preset_estimates` returns
  immediately — 200, no change, no warning. 🔴
- **Missing assumption row during preset application.** A new
  `DesignAssumptionModel(aeroplane_id, parameter_name)` is created with only
  `estimate_value` set — `active_source` falls to the column default
  (`"ESTIMATE"`). 🟡 The row is created outside `seed_defaults`, so its unit and
  design-choice metadata come from the catalogue at read time and stay
  consistent, but the row can exist before the rest of the catalogue does.
- **Unknown primary mission id in `missions`.** Falls back to the `trainer`
  preset's ranges while echoing the requested id as `active_mission_id`. 🟢
- **Unknown overlay ids.** Silently dropped from `target_polygons`. 🟢
- **Empty `mission_presets` table.** `RuntimeError` → HTTP 500, with an operator
  message naming the seed. The user-controlled id is deliberately absent from
  the log line (Sonar S5145) and present only in the exception message. 🟢
- **Missing mass.** `ctx["mass_kg"]` → `aeroplane.total_mass_kg` → `None`, which
  makes `wing_loading` a hole. 🟢
- **`field_length_service` unimportable** (no AeroSandbox on the platform). The
  module-level symbol is `None`; the axis degrades with a platform message. 🟢

## Dependencies

- **[`../design-assumptions/`](../design-assumptions/design.md)** — the write
  target of `_apply_preset_estimates` (five parameters, `estimate_value` only).
- **`aero-analysis`** — every Ist axis except `field_friendliness` reads
  `aeroplanes.assumption_computation_context` (BR-14).
- **`mission-and-sizing` / field lengths** —
  `field_length_service.compute_field_lengths_for_aeroplane` for the seventh
  axis, and `flight_envelope_n_max` for the manoeuvre axis.
- **`platform-core`** — `get_db()` (BR-78); the seeding runs at startup
  alongside `seed_default_types`.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| The default objective is returned, never persisted | `get_mission_objective` | 🟢 |
| A new default instance per call, so callers cannot mutate a singleton | `_default_objective` docstring | 🟢 |
| Preset application is triggered by a *change*, including the first create | `old_mission_type != payload.mission_type` | 🟢 |
| Presets write `estimate_value` exclusively | `_apply_preset_estimates` | 🟢 |
| An unknown mission id is a no-op, with rejection "deferred to the KPI service" | the docstring | 🔴 (the KPI service does not reject either) |
| Nine presets seeded idempotently by id | `seed_mission_presets` | 🟢 |
| `axis_ranges` stored as lists, exposed as tuples | `list_mission_presets`, `seed_mission_presets` | 🟢 |
| The KPI set is closed-form — no AeroBuildup re-run | module docstring | 🟢 |
| Zero and negative context values are "missing", not data | `_ctx_get` | 🟢 |
| A missing axis renders as a gap, not a zero | `_missing` | 🟢 |
| A degenerate range collapses to `0.0`, deliberately | `_normalise_score` docstring | 🟡 |
| The polar provenance chain survives a rejected fit (gh-681) | `_resolve_polar_inputs` | 🟢 |
| Empirical `ld_max` beats the parabolic formula (gh-636) | `_kpi_glide` | 🟢 |
| The Soll line for the user's own mission tracks their edits (gh-767) | `_objective_target_scores` | 🟢 |
| `field_friendliness` Soll is `1.0` by construction | same, with rationale | 🟢 |
| The field-length import is module-level so it is patchable | the `try/except ImportError` comment | 🟢 |
| An empty preset table fails loudly rather than returning an empty radar | `compute_mission_kpis` | 🟢 |
| The user-controlled mission id is kept out of the log record (S5145) | same | 🟢 |
| Field-performance inputs were migrated **out of** assumptions into the objective | `mission_objectives` columns, gh-548 | 🟢 |

## Internal State

| Table | Cardinality | Note |
|---|---|---|
| `mission_objectives` | **one per aeroplane** — `unique=True` on the FK, INDEXED, `ON DELETE CASCADE` | absent ⇒ the default is synthesised |
| `mission_presets` | global library, **String PK** | 🔴 no FK from `mission_objectives.mission_type` |
| `design_assumptions` | written here for five parameters | `estimate_value` only |
| `aeroplanes.assumption_computation_context` | read-only here | written by `aero-analysis` |

## Observability

- Every axis carries `formula` — a human-readable string rendered in the UI
  side-drawer, so a user can see *why* a number is what it is. 🟢
- Every axis carries `provenance` (`computed` / `estimated` / `missing`) and the
  `range_min` / `range_max` it was normalised against. 🟢
- A missing `field_friendliness` carries the service's own message as `warning`
  — pre-gh-562 that reason was only visible in the removed FieldLengthsPanel. 🟢
- `computed_at` (ISO-8601 UTC) and a 64-character `context_hash` accompany every
  KPI set. 🟡 Nothing server-side stores or compares the hash.
- The empty-preset-table failure logs an operator-facing message naming the
  Alembic migration and the seed. 🟢
- 🔴 An unknown `mission_type` produces **no signal at all** — no log, no
  warning, no response field.
- 🔴 A preset application produces no event, so nothing downstream records that
  five estimates changed.

## Constants 🟢

| Constant | Value | Where |
|---|---|---|
| `SEED_PRESETS` | nine `MissionPreset` entries | `app/services/mission_preset_seed.py` |
| `AxisName` | the seven axes | `app/schemas/mission_kpi.py` |
| `Provenance` | `computed` \| `estimated` \| `missing` | same |
| `RunwayType` | `grass` \| `asphalt` \| `belly` | `app/schemas/mission_objective.py` |
| `TakeoffMode` | `runway` \| `hand_launch` \| `bungee` \| `catapult` | same |
| `LandingSurface` | six values (gh-477) | same |
| objective defaults | cruise 18 · stall safety 1.8 · n 3.0 · L/D 12 · climb energy 22 · W/S 412 N/m² · field 50 m · runway 50 m grass · `t_static_N` 18 N · `takeoff_mode` runway | `_default_objective` |
| gravity in `wing_loading` | `9.81` | `_kpi_wing_loading` |
| `context_hash` | `sha256`, 64 hex chars, schema-enforced | `_hash_context`, `MissionKpiSet` |

## Risks and Gaps

- 🔴 **`power_to_weight` unit divergence (BR-MS34).** Seven presets write
  0.5–1.4 into a field catalogued as W/kg with a 220 default; two write 100.0
  W/kg. The matching chart's power-loading constraint and the `is_glider` test
  (`P/W ≤ 0`) both consume it, so selecting `trainer` currently declares a
  0.5 W/kg aircraft.
- 🟢 **An unknown `mission_type` fails visibly** (`Q-MS-10`/`P-WARN-0`) and `mission_type` gains a real reference constraint to `mission_presets.id` (`Q-CC-7`/`Q-CC-9`). Previously a silent no-op: Previously `_apply_preset_estimates` silently no-opped on an unknown
  `mission_type`** — a typo produces no error, no warning and no change, and the
  KPI service quietly normalises against `trainer` instead.
- 🟢 **A real reference constraint is added** (`Q-CC-7`/`Q-CC-9`). Previously a free-text String PK with no FK from
  `mission_objectives.mission_type`, so the two can drift apart; the trainer
  fallback exists only because of that.
- 🔴 **The preset writer bypasses `update_assumption`**, so five estimates can
  change without an `AssumptionChanged` event and without dirtying operating
  points — even when those estimates are the effective values.
- 🟡 **`wing_loading` ranges look unit-inconsistent** with the objective default
  (`20–120` vs `412 N/m²`); nothing in the code states which unit the ranges are
  in.
- 🟡 **A degenerate `axis_range` scores `0.0`, not `None`** — an unknown reported
  as a bad result.
- 🟡 **`context_hash` is a cache key with no cache.**
- 🟡 **`aeroplane.total_mass_kg` is a second mass source** behind
  `ctx["mass_kg"]`, with no statement of which is authoritative.
- 🟡 **`_default_objective` duplicates the column server-defaults** in Python;
  the two can drift.
