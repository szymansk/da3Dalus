# control-surface-naming

> Use-case specification, nested under the module
> [`avl-integration`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: avl-integration
> (gh-772 role → control-axis decomposition) and §Module: aero-analysis
> (🔴 GAP — control-surface naming divergence, open bug #955),
> `_reversa_sdd/domain.md` BR-9…BR-13, `_reversa_sdd/data-dictionary.md`
> §`ControlAxis`, ADR 0008.

## Overview

`control-surface-naming` is the single source of truth for **what a control
surface is called and how many degrees of freedom it has**. A trailing-edge
device carries a *role*; a role decomposes into one or two *control axes*; each
axis becomes one uniquely named control variable that AVL, AeroSandbox and the
trim-enrichment layer all address by the same string.

It is also the site of the project's most consequential open defect: three
services still key on the **raw DB name** instead of the canonical mixing name
(**open bug #955**), so on every V-tail, elevon or flaperon aircraft the
authority checks silently fall back to a hard-coded ±25° and report a phantom
surface. 🔴

## Responsibilities

- Decompose a role into one or two control axes with the correct symmetry, sign,
  gain and baseline deflection. 🟢
- Produce the canonical control-variable name for each axis. 🟢
- Guarantee that control-variable names are globally unique before any AVL
  geometry is written. 🟢
- Be the **one** implementation shared by the AVL builder, the ASB airplane
  builder and the trim-enrichment service. 🟢
- Parse a tagged name back into its role. 🟢

**Explicitly NOT this use case's responsibility:** the TED CRUD, the role
vocabulary itself and the mixing-gain validation (→ `wing-design`), emitting the
`CONTROL` block (→ [`../avl-geometry-generation/`](../avl-geometry-generation/requirements.md)),
the d-index map (→ [`../avl-run-and-parse/`](../avl-run-and-parse/requirements.md)),
and computing reserves from limits (→ `aero-analysis`, the **consumer** that is
currently broken).

## Business Rules

- **BR-9 — A role decomposes into control axes (gh-772, ADR 0008).** 🟢

  ```
  _DUAL_ROLE_AXES = { elevon:      (pitch, roll),
                      flaperon:    (lift,  roll),
                      ruddervator: (pitch, yaw)  }
  PRIMARY_AXES   = {pitch, lift}     # symmetric      SgnDup = +1
  SECONDARY_AXES = {roll,  yaw}      # antisymmetric  SgnDup = −1
  ```

  A dual-role surface emits **two** control variables on the same section:

  | axis | `SgnDup` | gain | `symmetric` | baseline deflection |
  |---|---|---|---|---|
  | primary (`pitch` \| `lift`) | `+1.0` | `mix_gain_primary` | `True` | the surface's deflection |
  | secondary (`roll` \| `yaw`) | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

  A single-axis role keeps its existing tagged name and `±1` sign **verbatim**.
- **BR-CSN1 — The secondary baseline is `0.0` for a specific reason.** 🟢
  AeroSandbox models a single axis, so the AeroBuildup fallback must never
  receive a roll/yaw deflection. Setting the antisymmetric baseline to zero is
  what makes the same `ControlAxis` list safe to hand to both solvers.
- **BR-11 — Control-variable names must be globally unique.** 🟢
  `axis_control_name` produces

  ```
  f"[{role}]{axis}_{sanitize(wing_key)}_{xsec_index}"
      e.g. "[ruddervator]pitch_htail_1"
  ```

  `assert_unique_control_names` (`control_surface_mixing.py:149-164`) raises on
  any duplicate. AVL **silently collapses** identically named `CONTROL` variables
  into a single DOF (avl_doc 778-789), coupling unrelated surfaces with no error
  message anywhere — so the assertion runs **before** any geometry is written.
- **BR-CSN2 — Per-surface duplication is legitimate; cross-surface duplication
  is not.** 🟢 The AVL builder duplicates a control onto sections `i` and `i+1`
  of the same surface (panel-strip interpolation), so the dedup is **per
  surface** and the uniqueness assertion is **across** surfaces.
- **BR-10 — `SgnDup` is a sign flag, never a magnitude.** 🟢
  `differential_ratio` is a **reporting-only** kinematic applied *after* trim for
  left/right display; it never alters the aero or trim solution and never reaches
  the `.avl` file (`control_surface_mixing.py:14-15`;
  `aeroplaneschema.py:372-381`).
- **BR-12 — Mixing fields are role-gated.** 🟢 (validated in `wing-design`, but
  the roles are this use case's vocabulary)
  `differential_ratio ≠ 1.0` is legal only for
  `DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}`;
  `mix_gain_secondary ≠ 1.0` only for
  `DUAL_ROLE_VALUES = {elevon, flaperon, ruddervator}`. Compared with
  `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; a `None` role (partial patch) skips
  the check entirely. Ranges: `mix_gain_*` `0 < x ≤ 5`, `differential_ratio`
  `0.3 < x ≤ 3`.
- **BR-CSN3 — A tagged name is parseable back into its role.** 🟢
  `_ROLE_TAG_RE = ^\[(\w+)\](.*)$` (`control_surface_mixing.py:25`). The role tag
  is what lets `_detect_control_capabilities` in `mission-and-sizing` classify an
  ASB airplane's controls into `has_pitch_control` / `has_roll_control` /
  `has_yaw_control` / `has_flap` without touching the database.
- **BR-CSN4 — One implementation, three consumers.** 🟢
  `control_surface_mixing.py` is shared by the AVL geometry builder, the ASB
  airplane builder and `trim_enrichment_service`. Duplicating the naming logic
  anywhere else re-opens #955 by construction.
- 🔴 **BR-13 — The canonical control name is the gh-772 mixing name — and three
  services ignore it (open bug #955).**

  | Site | What it keys on | Consequence |
  |---|---|---|
  | `trim_enrichment_service.build_deflection_limits_from_schema` (`:72-118`) | the raw TED `name` from the DB | `limits.get(name, (25.0, 25.0))` **misses** ⇒ the reserve/authority ratio is computed against a hard-coded **±25°**, not the aircraft's real hinge limit |
  | the gh-863 union in `compute_enrichment` | the same DB names | a **phantom surface at 0°** appears under a name no solver ever trims |
  | `retrim_service._find_pitch_control_name` | returns the DB `name` as a `trim_variable` | works **only** because the AeroBuildup trim service re-resolves display/role names — a change there breaks the background retrim silently |
  | `stability_service._find_trim_elevator` | substring match on `"elevator"` | never matches `[ruddervator]pitch_…` ⇒ `trim_elevator_deg` is `NULL` on exactly the aircraft where pitch authority matters most |

  **Always use the gh-772 mixing names.**

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Map each dual role to its (primary, secondary) axis pair | Must | `elevon → (pitch, roll)`, `flaperon → (lift, roll)`, `ruddervator → (pitch, yaw)` |
| RF-02 | Classify axes into symmetric and antisymmetric sets | Must | `{pitch, lift}` → `SgnDup +1`; `{roll, yaw}` → `SgnDup −1` |
| RF-03 | Emit two `ControlAxis` objects for a dual role | Must | Both carry the documented sign, gain, `symmetric` flag and baseline |
| RF-04 | Force the secondary axis's baseline deflection to `0.0` | Must | The AeroBuildup fallback never receives a roll/yaw deflection |
| RF-05 | Keep a single-axis role's tagged name and sign verbatim | Must | An `elevator` is unchanged by the decomposition |
| RF-06 | Produce `[{role}]{axis}_{wing_key}_{xsec_index}` | Must | `[ruddervator]pitch_htail_1` |
| RF-07 | Sanitise the wing key | Must | A wing named `"H Tail"` yields a name AVL accepts |
| RF-08 | Raise on any duplicate name across surfaces | Must | Two surfaces resolving to one name raise **before** geometry is written |
| RF-09 | Allow the same name repeated within one surface | Must | Panel-strip duplication does not raise |
| RF-10 | Parse a tagged name back into its role | Must | `[elevon]roll_wing_2` → role `elevon` |
| RF-11 | Be the only implementation of the naming rule | Must | No other module derives a control name independently |
| RF-12 | Key deflection limits by the mixing name | **Must (open)** | 🔴 #955 — a ruddervator's reserve must use its real TED limits |
| RF-13 | Resolve the pitch control by the mixing name | **Must (open)** | 🔴 #955 — the background retrim and `trim_elevator_deg` must work on a V-tail |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Uniqueness is asserted **before** any AVL geometry is written, because AVL fails silently on a collision | `assert_unique_control_names:149-164` | 🟢 |
| Correctness | One module owns the naming rule, shared by three consumers | `control_surface_mixing.py` (ADR 0008) | 🟢 |
| Correctness | The antisymmetric baseline is zero, keeping the same axis list valid for a single-axis solver | gh-772 | 🟢 |
| Interoperability | The name carries its role as a parseable tag, so capability detection needs no database access | `_ROLE_TAG_RE:25` | 🟢 |
| Testability | The whole use case is pure functions over primitives — no DB, no solver, no binary | module structure | 🟢 |
| Traceability | `ControlAxis` records `role`, `axis`, `sgn_dup`, `gain`, `symmetric`, `hinge_point`, `deflection`, so a name can be explained | `control_surface_mixing.py:41` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Role decomposition

  Scenario: An elevon becomes pitch and roll
    Given a trailing-edge device with role "elevon" and deflection 10 degrees
    When the control axes are resolved
    Then a pitch axis exists with SgnDup +1, gain mix_gain_primary,
         symmetric true and baseline deflection 10
    And a roll axis exists with SgnDup -1, gain mix_gain_secondary,
         symmetric false and baseline deflection 0.0

  Scenario: A flaperon becomes lift and roll
    Given a role of "flaperon"
    Then the primary axis is "lift" and the secondary axis is "roll"

  Scenario: A ruddervator becomes pitch and yaw
    Given a role of "ruddervator"
    Then the primary axis is "pitch" and the secondary axis is "yaw"

  Scenario: A single-axis role is untouched
    Given a role of "elevator"
    Then exactly one control axis is produced
    And its tagged name and sign are unchanged

Feature: Naming

  Scenario: The canonical name
    Given role "ruddervator", axis "pitch", wing key "htail" and index 1
    Then the control name is "[ruddervator]pitch_htail_1"

  Scenario: The wing key is sanitised
    Given a wing named "H Tail"
    Then the emitted name contains no character AVL would reject

  Scenario: A name is parseable back to its role
    Given the name "[elevon]roll_wing_2"
    Then the extracted role is "elevon"

Feature: Uniqueness

  Scenario: A cross-surface collision is refused
    Given two surfaces whose controls resolve to the same name
    When assert_unique_control_names runs
    Then it raises
    And no AVL geometry is written
    # AVL would silently collapse them into one DOF

  Scenario: Panel-strip duplication is allowed
    Given the same control name on sections i and i+1 of ONE surface
    Then the build succeeds

Feature: The #955 divergence (documented current behaviour)

  Scenario: Deflection limits miss on a dual-role surface
    Given a ruddervator whose control variable is "[ruddervator]pitch_htail_1"
    And deflection limits keyed by the DB name "ruddervator_right"
    When the trim enrichment is computed
    Then the reserve is computed against the hard-coded 25 degree limits
    And a phantom surface at 0 degrees appears under the DB name
    # 🔴 documented defect, not desired behaviour

  Scenario: The trim elevator is never found on a V-tail
    Given an aircraft whose only pitch control is "[ruddervator]pitch_htail_1"
    When the stability summary is computed
    Then trim_elevator_deg is null
    # 🔴 substring match on "elevator" cannot match

  Scenario: After the fix
    Given the same ruddervator
    When the trim enrichment is computed
    Then the reserve uses the aircraft's real TED deflection limits
    And no phantom surface is reported
    And trim_elevator_deg reports the pitch-axis deflection
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Role → axis decomposition (RF-01…RF-05) | Must | The only mechanism that lets a mixed surface have two DOFs; ADR 0008 |
| Canonical naming (RF-06, RF-07) | Must | Every solver, the enrichment layer and the AVL d-index map address controls by this string |
| Uniqueness assertion (RF-08, RF-09) | Must | AVL fails **silently** on a collision — nothing downstream could detect it |
| Single implementation (RF-11) | Must | Duplicating the rule re-creates #955 by construction |
| Role tag parseability (RF-10) | Must | Capability gating in `mission-and-sizing` depends on it |
| Keying limits by the mixing name (RF-12) | **Must (open)** | 🔴 today every dual-role aircraft gets a wrong authority verdict |
| Pitch-control resolution by mixing name (RF-13) | **Must (open)** | 🔴 today a V-tail reports no trim deflection and the retrim works only by accident |
| Marking a reserve computed against the fallback limits | Should | ADR 0012 — a fallback should be visible, not silent |
| Trimming the antisymmetric axis with AeroBuildup | Won't | ASB models one axis; AVL only (ADR 0003) |
| A third axis per surface | Won't | No role in the vocabulary needs one |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/control_surface_mixing.py` | `_DUAL_ROLE_AXES` (`:29-33`), `PRIMARY_AXES`, `SECONDARY_AXES`, `axis_control_name` (`:76-84`), `assert_unique_control_names` (`:149-164`), `_ROLE_TAG_RE` (`:25`), `ControlAxis` (`:41`), the `differential_ratio` note (`:14-15`), single-axis passthrough (`:134-146`) | 🟢 |
| `app/services/avl_geometry_service.py` | `_build_controls_for_wing`, `build_avl_geometry_file` (the per-surface dedup + cross-surface assertion) | 🟢 |
| `app/converters/model_schema_converters.py` | the ASB airplane builder consuming the same `ControlAxis` list | 🟢 |
| `app/schemas/aeroplaneschema.py` | `_validate_mix_fields` (`:51-78`), `differential_ratio` (`:372-381`), `DUAL_ROLE_VALUES`, `DIFFERENTIAL_ROLE_VALUES` | 🟢 (owned by `wing-design`) |
| `app/services/trim_enrichment_service.py` | `build_deflection_limits_from_schema` (`:72-118`), the gh-863 union | 🔴 keys on the DB name (#955) |
| `app/services/retrim_service.py` | `_find_pitch_control_name` | 🔴 returns the DB name (#955) |
| `app/services/stability_service.py` | `_find_trim_elevator` | 🔴 substring match (#955) |
| `app/services/operating_point_generator_service.py` | `_detect_control_capabilities` (consumes the role tag) | 🟢 |
