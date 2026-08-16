# control-surface-mixing — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md). ADR 0008.

## Prerequisites

- [ ] `wing_xsec_details` 1:1 side table available (use case
      [`cross-section-crud`](../cross-section-crud/tasks.md) T-03) — the TED
      hangs off it.
- [ ] `_assert_non_terminal_xsec_or_raise` in place
      ([`cross-section-crud`](../cross-section-crud/tasks.md) T-08) — every
      route here targets a segment, never the terminal station.
- [ ] `components` table available for the servo's `component_id` FK.
- [ ] `app/core/exceptions.py` hierarchy and the global error envelope
      (`ValidationError → 422`, `NotFoundError → 404`).
- [ ] `get_db()` owning the transaction (ADR 0009).

## Tasks

- [ ] **T-01 — `wing_xsec_trailing_edge_devices` table and model.**
  `wing_xsec_detail_id` FK `ON DELETE CASCADE` and **unique** (1:1);
  `name` (nullable), `role` (**`NOT NULL`, default `'other'`**), `label`,
  `rel_chord_root` / `rel_chord_tip` (0–1), `hinge_spacing` /
  `side_spacing_root` / `side_spacing_tip` (**mm**), `servo_placement`
  (`top`|`bottom`), `rel_chord_servo_position` / `rel_length_servo_position`
  (0–1), `positive_deflection_deg` / `negative_deflection_deg`,
  `deflection_deg`, `trailing_edge_offset_factor`, `hinge_type`
  (`middle`|`top`|`top_simple`|`round_inside`|`round_outside`), `symmetric`,
  and the three gh-772 columns **`NOT NULL` defaulting to `1.0`**:
  `mix_gain_primary`, `mix_gain_secondary`, `differential_ratio`; plus
  `servo_index`.
  - Legacy origin: `app/models/aeroplanemodel.py:147`
  - Definition of done: a second TED for the same `wing_xsec_detail_id` raises
    an `IntegrityError`; a TED inserted with no mixing values reads back
    `1.0 / 1.0 / 1.0` and `role = 'other'`.
  - Confidence: 🟢

- [ ] **T-02 — `wing_xsec_ted_servos` table and model.**
  `ted_id` FK `ON DELETE CASCADE` and **unique** (1:1), `component_id` FK →
  `components.id`, and the pocket geometry in **mm**, all nullable: `length`,
  `width`, `height`, `leading_length`, `latch_z`, `latch_x`, `latch_thickness`,
  `latch_length`, `cable_z`, `screw_hole_lx`, `screw_hole_d`.
  - Legacy origin: `app/models/aeroplanemodel.py:190`
  - Definition of done: deleting the TED cascades the servo away; deleting the
    servo leaves the TED.
  - Confidence: 🟢

- [ ] **T-03 — The `servo` union property.**
  Return `servo_data` when the 1:1 row is present, else the `servo_index`
  integer.
  - Legacy origin: `app/models/aeroplanemodel.py:183-187`
  - Definition of done: both branches are covered; the return type is documented
    as `Servo | int`. `servo_data` is canonical for new records and
    `servo_index` is deprecated (`Q-WD-3 ①`); the union stays readable so
    existing rows resolve.
  - Confidence: 🟢

- [ ] **T-04 — `_DUAL_ROLE_AXES` and the axis sets.**

  ```
  _DUAL_ROLE_AXES = { "elevon":      ("pitch", "roll"),
                      "flaperon":    ("lift",  "roll"),
                      "ruddervator": ("pitch", "yaw") }
  PRIMARY_AXES   = {"pitch", "lift"}
  SECONDARY_AXES = {"roll",  "yaw"}
  ```

  - Legacy origin: `app/services/control_surface_mixing.py:29-33`
  - Definition of done: the three dual roles map to exactly these pairs; every
    primary axis is in `PRIMARY_AXES` and every secondary in `SECONDARY_AXES`
    (a consistency test over the table).
  - Confidence: 🟢

- [ ] **T-05 — Dual-role emission with the sign/gain/baseline table.**
  Emit **two** `CONTROL` variables on the same section:

  | axis | `sgn_dup` | gain | `symmetric` | baseline |
  |---|---|---|---|---|
  | primary | `+1.0` | `mix_gain_primary` | `True` | `deflection_deg` |
  | secondary | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

  The secondary baseline is `0.0` so the AeroBuildup fallback never receives a
  roll/yaw deflection its single-axis model cannot represent.
  - Legacy origin: `app/services/control_surface_mixing.py:126-128`
  - Definition of done: an `elevon` with `deflection_deg = 10` yields a pitch
    variable with baseline 10 and a roll variable with baseline **0.0**; a test
    asserts the secondary baseline is zero *regardless* of `deflection_deg`.
  - Confidence: 🟢

- [ ] **T-06 — Single-axis passthrough.**
  A role not in `_DUAL_ROLE_AXES` keeps its existing tagged name and its `±1`
  sign **verbatim** — exactly one variable is emitted.
  - Legacy origin: `app/services/control_surface_mixing.py:134-146`
  - Definition of done: an `aileron` emits one variable whose name and sign are
    identical to the pre-gh-772 output; a golden-file test pins this so the
    compatibility guarantee cannot silently regress.
  - Confidence: 🟢

- [ ] **T-07 — `axis_control_name`.**

  ```
  [{role}]{axis}_{wing_key}_{xsec_index}
  e.g.  [ruddervator]pitch_htail_1
  ```

  - Legacy origin: `app/services/control_surface_mixing.py:76-84`
  - Definition of done: the exact string for a known `(role, axis, wing_key,
    index)` tuple is asserted character-for-character, brackets included.
  - Confidence: 🟢

- [ ] **T-08 — `assert_unique_control_names`.**
  Collect every resolved control name across every surface on the aircraft and
  raise on the first duplicate, **before** any AVL geometry is written.
  - Legacy origin: `app/services/control_surface_mixing.py:149-164`
  - Definition of done: two surfaces resolving to the same name raise; the test
    asserts no `.avl` content was produced. The exception maps to **422**
    (`Q-WD-9 ①`) — a duplicate name is user-correctable input, and the message
    must name the colliding control.
  - Confidence: 🟢

- [ ] **T-09 — `_validate_mix_fields` role gate.**

  ```
  DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}
  DUAL_ROLE_VALUES         = {elevon, flaperon, ruddervator}

  if role is None: return                       # partial patch — skip entirely
  if not isclose(differential_ratio, 1.0, rel_tol=1e-9, abs_tol=1e-9)
         and role not in DIFFERENTIAL_ROLE_VALUES: raise
  if not isclose(mix_gain_secondary, 1.0, rel_tol=1e-9, abs_tol=1e-9)
         and role not in DUAL_ROLE_VALUES: raise
  ```

  - Legacy origin: `app/schemas/aeroplaneschema.py:51-78`
  - Definition of done: a role × field matrix test; `math.isclose` is used (a
    value of `0.9999999999999999` passes as unity, which `==` would reject).
  - Confidence: 🟢

- [ ] **T-10 — Mixing field ranges.**
  `mix_gain_primary` and `mix_gain_secondary` `0 < x ≤ 5`;
  `differential_ratio` `0.3 < x ≤ 3`.
  - Legacy origin: `app/schemas/aeroplaneschema.py:287`
    (`TrailingEdgeDeviceDetailSchema`)
  - Definition of done: boundary tests — `mix_gain_primary` `0` → 422, `5.0` →
    200, `5.1` → 422; `differential_ratio` `0.3` → 422, `0.31` → 200, `3.0` →
    200, `3.1` → 422.
  - Confidence: 🟢

- [ ] **T-11 — `TrailingEdgeDevicePatchSchema`.**
  `extra="forbid"` plus a non-empty-patch validator.
  - Legacy origin: `app/schemas/aeroplaneschema.py:397`
  - Definition of done: `{}` → 422; an unknown key → 422; a single known field →
    200.
  - Confidence: 🟢

- [ ] **T-12 — `ControlSurfaceSchema` and the CAD subsets.**
  `ControlSurfaceSchema` with `hinge_point` default `0.8` and `symmetric`
  default `True` (l.102); `ControlSurfaceCadDetailsSchema` (l.156) and its patch
  variant (l.184), which requires ≥ 1 field.
  - Legacy origin: `app/schemas/aeroplaneschema.py:102, 156, 184`
  - Definition of done: an omitted `hinge_point` reads back as `0.8`; an empty
    `cad_details` patch → 422.
  - Confidence: 🟢

- [ ] **T-13 — The computed `control_surface` projection.**
  `WingXSecModel.control_surface` projects the 1:1 TED row; it is **never**
  stored separately.
  - Legacy origin: `app/models/aeroplanemodel.py:241-276`
  - Definition of done: changing `rel_chord_root` on the TED changes the
    projection on the next read with no second write; a test asserts no
    `control_surface` table exists.
  - Confidence: 🟢

- [ ] **T-14 — TED CRUD routes.**
  `GET` / `PATCH` / `DELETE` on `/trailing_edge_device`, applying the
  terminal-station guard, T-09, T-10 and T-11.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` TED routes
  - Definition of done: `differential_ratio = 1.5` on `flap` → 422; on `aileron`
    → 200; a write to the terminal station → 422.
  - Confidence: 🟢

- [ ] **T-15 — Servo CRUD routes.**
  `GET` / `PATCH` / `DELETE` on `/trailing_edge_device/servo`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` servo routes;
    `app/schemas/Servo.py:6-13`
  - Definition of done: `DELETE` removes only the servo; the TED survives.
    Deleting the TED cascades the servo away.
  - Confidence: 🟢

- [ ] **T-16 — `control_surface`, `cad_details` and `servo_details` routes.**
  `GET` / `PATCH` / `DELETE` on `/control_surface`,
  `/control_surface/cad_details` and
  `/control_surface/cad_details/servo_details`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` control-surface
    routes
  - Definition of done: patching `cad_details` leaves the ASB projection fields
    untouched — a field-by-field assertion, not just a status check.
  - Confidence: 🟢

- [ ] **T-17 — Converter: overwrite the x-sec control surface with the
  TED-derived one.**
  In `_build_segment_details`, the segment's own TED-derived control surface
  **replaces** the x-sec-derived one, so `_merge_ted_with_control_surface`
  cannot resurrect a phantom TED on round-trip.
  - Legacy origin: `app/converters/model_schema_converters.py:960-995`
  - Definition of done: a wing whose segment 0 has no TED still has no TED after
    an ASB round-trip. (Shared with
    [`cross-section-crud`](../cross-section-crud/tasks.md) T-18 — implement once,
    test from both sides.)
  - Confidence: 🟢

- [ ] **T-18 — Keep `differential_ratio` out of the physics.**
  Apply it **only** post-trim, for left/right display. It must not appear in the
  AVL geometry, the ASB model, or the trim solve.
  - Legacy origin: `app/services/control_surface_mixing.py:14-15`;
    `app/schemas/aeroplaneschema.py:372-381`
  - Definition of done: a test changes `differential_ratio` from 1.0 to 2.0 and
    asserts the generated AVL geometry is **byte-identical** and the trim result
    numerically identical; only the reported left/right deflections differ.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path:** an `elevon` with `deflection_deg = 10` yields
      `[elevon]pitch_<wing>_<i>` (`+1`, `mix_gain_primary`, symmetric, baseline
      10) and `[elevon]roll_<wing>_<i>` (`−1`, `mix_gain_secondary`,
      antisymmetric, baseline `0.0`) — see
      [`requirements.md`](requirements.md) Acceptance Criteria.
- [ ] **TT-02 — Failure:** two surfaces resolving to the same control name raise
      before any AVL geometry is written.
- [ ] **TT-03 — Dual-role table:** `flaperon → (lift, roll)`,
      `ruddervator → (pitch, yaw)`, `elevon → (pitch, roll)`; each with the full
      sign/gain/symmetry/baseline assertion.
- [ ] **TT-04 — Secondary baseline invariant:** for every dual role and for
      `deflection_deg ∈ {-20, 0, 10, 25}`, the secondary baseline is always
      `0.0`.
- [ ] **TT-05 — Single-axis golden file:** an `aileron`'s emitted name and sign
      are byte-identical to the pre-gh-772 output.
- [ ] **TT-06 — Name format:** `axis_control_name("ruddervator", "pitch",
      "htail", 1) == "[ruddervator]pitch_htail_1"`.
- [ ] **TT-07 — Role gate matrix:** every `(role, field, value)` combination
      across `DIFFERENTIAL_ROLE_VALUES`, `DUAL_ROLE_VALUES` and the excluded
      roles.
- [ ] **TT-08 — `isclose` tolerance:** `0.9999999999999999` passes as unity on a
      `flap`; `1.0000001` does not.
- [ ] **TT-09 — Partial patch skip:** a patch carrying only `label` succeeds on a
      `flap` even though the stored `mix_gain_secondary` would be illegal if
      revalidated. **Pin the current behaviour**; the validation hole is
      recorded and `role` gains a CHECK constraint (`Q-WD-3 ④`).
- [ ] **TT-10 — Range boundaries:** all eight boundary cases from T-10.
- [ ] **TT-11 — Empty and unknown-field patches** → 422.
- [ ] **TT-12 — Projection follows the TED:** a `rel_chord_root` change shows up
      in `control_surface` with no second write.
- [ ] **TT-13 — Subset isolation:** patching `cad_details` leaves every ASB
      projection field unchanged.
- [ ] **TT-14 — Cascade matrix:** delete servo → TED survives; delete TED →
      servo gone; delete station → TED and servo gone.
- [ ] **TT-15 — `differential_ratio` isolation:** byte-identical AVL geometry
      and identical trim across a ratio change.
- [ ] **TT-16 — Phantom-TED guard:** an ASB round-trip on a segment with no TED
      does not create one.
- [ ] **TT-17 — Defaults:** a TED created with no mixing values reads back
      `1.0 / 1.0 / 1.0` and `role = 'other'`; both gates then reject a non-unity
      value on it.

## Data Migration Tasks

- [ ] **TM-01 — Backfill the gh-772 mixing columns on pre-gh-772 rows.**
      `mix_gain_primary`, `mix_gain_secondary` and `differential_ratio` are
      `NOT NULL DEFAULT 1.0`; confirm the migration set `1.0` rather than
      leaving nulls that would break the role gate's `isclose` call. 🟡
- [ ] **TM-02 — Invalidate stored results for the three affected aircraft.**
      🟢 **Measured 2026-08-15:** 7 `ruddervator` surfaces exist, on
      **`tdfalconv2`, `Olek` and `eHawk`**. No `elevon` or `flaperon` rows exist.
      Those three aircraft were trimmed with the hard-coded ±25° fallback rather
      than their real deflection limits, so their stored trim and stability
      results must be invalidated once `Q-WD-1`'s resolver lands. The affected
      set is identified; the task is execution, not investigation.
- [x] **TM-03 — Illegal role/mixing pairs: none exist.** 🟢 **Measured
      2026-08-15:** **0 rows** carry a non-unity `mix_gain_secondary` on a
      non-dual role. The validation hole (the gate is skipped when `role` is
      `None` on a patch) is real, but it has not yet produced bad data, so
      stricter validation can be enabled without a migration.
- [x] **TM-04 — Unknown `role` values: none exist.** 🟢 **Measured 2026-08-15:**
      every stored `role` is within the legal set
      (`aileron` 16, `rudder` 8, `elevator` 8, `ruddervator` 7, `other` 6,
      `flap` 2). The CHECK constraint from `Q-WD-3 ④` can therefore be added
      without backfilling.

> **Two measurements worth carrying to other units.** `hinge_type` is `top` on 40
> rows, `middle` on 1, and **NULL on 6** — so the topology-vs-DB default
> divergence (`Q-WD-3 ③`) is not hypothetical: six stored surfaces already rely
> on `TrailingEdgeDevice`'s `"top"` default at build time, which is exactly why
> the topology layer must remain the single authority. And **no row uses
> `round_inside` or `round_outside`**, which confirms the maintainer's judgement
> at `Q-CT-5` that the two unimplemented hinge creators are *"kein Schaden für
> den Beta-Test-Benutzer"* — nobody has selected them.

## Suggested Order

1. **T-01 → T-03** first: the two tables and the union property are the
   foundation. T-01 must land with the three gh-772 columns `NOT NULL DEFAULT
   1.0`, or every later gate has to handle nulls.
2. **T-04 → T-08** next, and as **pure functions with no database**: the whole
   decomposition is deterministic given `(role, deflection, gains, wing_key,
   index)`, so it should be fully unit-tested before any route exists. T-05 and
   T-06 both block on T-04; T-07 blocks T-08.
3. **T-09 → T-12**: the schema layer. T-09 blocks on nothing but must be built
   before T-14, since the gate is the reason the TED route exists in its current
   form. T-10 and T-11 are independent.
4. **T-13** after T-01 — the projection needs the TED row to project.
5. **T-14 → T-16**: the REST layer, thin over what is already tested. T-14
   blocks on T-09/T-10/T-11 and on the `cross-section-crud` terminal guard.
6. **T-17** jointly with `cross-section-crud` T-18 — implement once, test from
   both use cases.
7. **T-18** last, and as a **standing invariant test** rather than a feature: it
   asserts an absence (no physics dependence), so it is most valuable once the
   AVL and trim paths exist to be compared against.

## Pending Gaps (🔴)

- **Open bug #955 — the canonical control name has diverged.**
  `trim_enrichment_service`, `retrim_service` and `stability_service` key on the
  raw DB TED name instead of the gh-772 mixing name, so a dual-role aircraft
  falls back to a hard-coded ±25° and reports a phantom 0° surface. Owned by
  `aero-analysis` — but should this use case expose a resolver they are required
  to call, so the divergence becomes impossible rather than merely fixed once?
- **What does a duplicate control name return to the client?** The exception type
  raised by `assert_unique_control_names` was not captured. A 422 (user can
  rename) and a 500 (internal fault) imply very different UX.
- **The `role is None` skip is a validation hole.** A multi-step patch can leave
  a `flap` carrying a non-unity `mix_gain_secondary`. Should changing `role`
  re-validate the existing mixing fields?
- **`servo` is a union by convention.** Is `WingXSecTedServoModel` or the `int`
  `servo_index` canonical for new records (`aeroplanemodel.py:183-187`)?
- **`Servo` requires fields the DB allows to be NULL.** How should a legacy row
  with a `NULL` dimension be surfaced — rejected, defaulted, or made optional?
- **Topology vs DB default divergence, and the 25° collision.** The topology
  layer defaults `positive/negative_deflection_deg` to 25° while the DB defaults
  to `NULL` — and 25° is also the value the #955 fallback hard-codes. Which
  layer supplies the effective default on a CAD build, and can the two 25°s be
  told apart in a report?
- **`role` has no database-level constraint.** Should the legal
  `ControlSurfaceRole` set be enforced by a CHECK constraint or enum, given that
  an unknown role is silently treated as single-axis?
- **`deflection_deg` doubles as the primary axis baseline.** Is a stored non-zero
  commanded deflection meant to persist into every subsequent trim, or should it
  be reset?
