# control-surface-mixing — Technical Design

> Use-case design, nested under the module [`wing-design`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module REST contract: [`../contracts.md`](../contracts.md). ADR 0008.

## Interface

### REST surface owned by this use case 🟢

Base: `/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{i}`
(`app/api/v2/endpoints/aeroplane/wings.py`). All of these target the **inboard**
station of a segment; a write to the terminal station is rejected with 422 by
`_assert_non_terminal_xsec_or_raise` (see
[`../cross-section-crud/design.md`](../cross-section-crud/design.md) §F4).

| Method | Path suffix | Operation | Status codes |
|---|---|---|---|
| GET | `/trailing_edge_device` | read the TED | 200 · 404 · 500 |
| PATCH | `/trailing_edge_device` | partial update, role-gated | 200 · 404 · **422** · 500 |
| DELETE | `/trailing_edge_device` | delete the TED (servo cascades) | 200 · 404 · 500 |
| GET | `/trailing_edge_device/servo` | read the servo | 200 · 404 · 500 |
| PATCH | `/trailing_edge_device/servo` | partial servo update | 200 · 404 · 422 · 500 |
| DELETE | `/trailing_edge_device/servo` | delete only the servo | 200 · 404 · 500 |
| GET | `/control_surface` | read the ASB projection | 200 · 404 · 500 |
| PATCH | `/control_surface` | patch the ASB projection | 200 · 404 · 422 · 500 |
| DELETE | `/control_surface` | delete the projection | 200 · 404 · 500 |
| GET | `/control_surface/cad_details` | CAD-only subset | 200 · 404 · 500 |
| PATCH | `/control_surface/cad_details` | patch the CAD-only subset | 200 · 404 · 422 · 500 |
| DELETE | `/control_surface/cad_details` | delete the CAD-only subset | 200 · 404 · 500 |
| GET | `/control_surface/cad_details/servo_details` | servo subset | 200 · 404 · 500 |
| PATCH | `/control_surface/cad_details/servo_details` | patch the servo subset | 200 · 404 · 422 · 500 |
| DELETE | `/control_surface/cad_details/servo_details` | delete the servo subset | 200 · 404 · 500 |

### Mixing surface — `app/services/control_surface_mixing.py` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `_DUAL_ROLE_AXES` | `{elevon: (pitch, roll), flaperon: (lift, roll), ruddervator: (pitch, yaw)}` | l.29-33 |
| `PRIMARY_AXES` | `{"pitch", "lift"}` — the symmetric component | l.29-33 |
| `SECONDARY_AXES` | `{"roll", "yaw"}` — the antisymmetric component | l.29-33 |
| `axis_control_name` | `(role, axis, wing_key, xsec_index) -> str` → `[{role}]{axis}_{wing_key}_{xsec_index}` | l.76-84 |
| dual-role emission | two `CONTROL` variables, secondary baseline `0.0` | l.126-128 |
| single-axis passthrough | existing tagged name and `±1` sign kept verbatim | l.134-146 |
| `assert_unique_control_names` | raises on any duplicate name | l.149-164 |
| module docstring | states the two invariants (BR-10) | l.14-15 |

### Validation surface — `app/schemas/aeroplaneschema.py` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `_validate_mix_fields` | the role gate; `DIFFERENTIAL_ROLE_VALUES` / `DUAL_ROLE_VALUES` | l.51-78 |
| `ControlSurfaceSchema` | ASB-compatible projection; `hinge_point` default `0.8`, `symmetric` default `True` | l.102 |
| `ControlSurfaceCadDetailsSchema` / `…PatchSchema` | CAD-only TED subset; patch variants require ≥1 field | l.156 / l.184 |
| `TrailingEdgeDeviceDetailSchema` | full TED contract; `mix_gain_*` `0 < x ≤ 5`, `differential_ratio` `0.3 < x ≤ 3` | l.287 |
| `TrailingEdgeDevicePatchSchema` | partial update; `extra="forbid"` + non-empty-patch validator | l.397 |
| `differential_ratio` note | reporting-only kinematic, post-trim | l.372-381 |

### Data model 🟢

`wing_xsec_trailing_edge_devices` (`WingXSecTrailingEdgeDeviceModel`,
`app/models/aeroplanemodel.py:147`) — `wing_xsec_detail_id` FK
`ON DELETE CASCADE` and **unique** (1:1), plus:

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `name` | String | no | `NULL` | raw device name — **the name #955 consumers still key on** |
| `role` | String | **yes** | `'other'` | a `ControlSurfaceRole` value |
| `label` | String | no | `NULL` | user-facing display name |
| `rel_chord_root` / `rel_chord_tip` | Float | no | `NULL` | hinge position 0–1 |
| `hinge_spacing`, `side_spacing_root`, `side_spacing_tip` | Float | no | `NULL` | **mm** |
| `servo_placement` | String | no | `NULL` | `top` \| `bottom`; the schema coerces `NULL` → `top` |
| `rel_chord_servo_position` / `rel_length_servo_position` | Float | no | `NULL` | 0–1 |
| `positive_deflection_deg` / `negative_deflection_deg` | Float | no | `NULL` | topology default **25°** |
| `deflection_deg` | Float | no | `NULL` | current commanded deflection — the primary axis baseline |
| `trailing_edge_offset_factor` | Float | no | `NULL` | topology default `1.0` |
| `hinge_type` | String | no | `NULL` | `middle` \| `top` \| `top_simple` \| `round_inside` \| `round_outside`; topology default `"top"` |
| `symmetric` | Boolean | no | `NULL` | symmetric vs antisymmetric throw |
| `mix_gain_primary` | Float | **yes** | `1.0` | gh-772; schema `0 < x ≤ 5` |
| `mix_gain_secondary` | Float | **yes** | `1.0` | gh-772; ≠ 1.0 only for dual roles |
| `differential_ratio` | Float | **yes** | `1.0` | gh-772; **reporting only**; schema `0.3 < x ≤ 3` |
| `servo_index` | Integer | no | `NULL` | alternative to the 1:1 `servo_data` row |

`wing_xsec_ted_servos` (`WingXSecTedServoModel`, l.190) — `ted_id` FK
`ON DELETE CASCADE` and **unique** (1:1), `component_id` FK → `components.id`,
and the pocket geometry in **mm**: `length`, `width`, `height`,
`leading_length`, `latch_z`, `latch_x`, `latch_thickness`, `latch_length`,
`cable_z`, `screw_hole_lx`, `screw_hole_d` — **all nullable**, while the
Pydantic `Servo` schema requires every one as a `NonNegativeFloat`
(`app/schemas/Servo.py:6-13`).

The `servo` property returns `servo_data` when present, else `servo_index`
(l.183-187) — a **union type by convention**, not by schema.

`WingXSecModel.control_surface` (l.241-276) is a **computed projection** over
the TED, not a stored row.

## Main Flow

### F1 — Resolve control axes for one surface 🟢

1. Read the surface's `role`.
2. Look it up in `_DUAL_ROLE_AXES` (l.29-33):

   ```
   elevon      → (pitch, roll)
   flaperon    → (lift,  roll)
   ruddervator → (pitch, yaw)
   ```

3. **Dual role** — emit **two** `CONTROL` variables on the same section (AVL
   sums multiple `CONTROL` lines per section):

   | axis | `sgn_dup` | gain | `symmetric` | baseline deflection |
   |---|---|---|---|---|
   | primary (`pitch` or `lift`) | `+1.0` | `mix_gain_primary` | `True` | the surface's `deflection_deg` |
   | secondary (`roll` or `yaw`) | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

   The secondary baseline is **0.0** so the AeroBuildup fallback never feeds a
   roll/yaw deflection into the single-axis ASB model (l.126-128).
4. **Single-axis role** — keep the existing tagged name and the `±1` sign
   **verbatim** (l.134-146). This is what let gh-772 ship without changing any
   existing single-axis aircraft.

### F2 — Name generation (`axis_control_name`, l.76-84) 🟢

```
[{role}]{axis}_{wing_key}_{xsec_index}

e.g.  [ruddervator]pitch_htail_1
      [elevon]roll_wing_2
```

The role is embedded in brackets so the name is self-describing in an `.avl`
file, and the `wing_key` + `xsec_index` suffix is what makes it globally unique
across surfaces.

### F3 — Uniqueness assertion (`assert_unique_control_names`, l.149-164) 🟢

1. Collect every resolved control name across every surface on the aircraft.
2. Raise on the first duplicate.
3. This runs **before** any AVL geometry is written.

The reason is stated in the code: **AVL silently collapses identically named
`CONTROL` variables into a single DOF.** There is no AVL error and no warning —
the run completes and returns a wrong answer. The assertion is the only defence.

### F4 — Role-gated write validation (`_validate_mix_fields`,
`aeroplaneschema.py:51-78`) 🟢

```
DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}
DUAL_ROLE_VALUES         = {elevon, flaperon, ruddervator}

if role is None:                     # partial patch — skip entirely
    return

if not isclose(differential_ratio, 1.0, rel_tol=1e-9, abs_tol=1e-9)
       and role not in DIFFERENTIAL_ROLE_VALUES:
    raise

if not isclose(mix_gain_secondary, 1.0, rel_tol=1e-9, abs_tol=1e-9)
       and role not in DUAL_ROLE_VALUES:
    raise
```

Comparison is `math.isclose`, not `==`, so a value that has round-tripped
through JSON as `0.9999999999999999` is still treated as unity. Schema ranges
are enforced separately by the field constraints: `mix_gain_*` `0 < x ≤ 5`,
`differential_ratio` `0.3 < x ≤ 3`.

### F5 — TED write and the projection 🟢

1. Resolve the wing and station; reject the terminal station (422).
2. Validate against `TrailingEdgeDevicePatchSchema` — `extra="forbid"` plus a
   non-empty-patch validator (l.397), then `_validate_mix_fields`.
3. Upsert the 1:1 `wing_xsec_trailing_edge_devices` row.
4. `WingXSecModel.control_surface` re-projects automatically on the next read
   (l.241-276) — there is **no** second row to keep in sync.
5. On conversion, `_build_segment_details` overwrites the x-sec-derived control
   surface with this TED-derived one, so
   `_merge_ted_with_control_surface` cannot resurrect a phantom TED
   (`model_schema_converters.py:960-995`).

### F6 — `differential_ratio` application (post-trim, reporting only) 🟢

`differential_ratio` is applied **after** the trim solution, purely to display
distinct left/right throws. It never enters the AVL geometry, the ASB model, or
the trim solve (`control_surface_mixing.py:14-15`;
`aeroplaneschema.py:372-381`). Consequently a change to it must produce a
byte-identical geometry and an identical trim result.

## Alternative Flows

- **Unknown aeroplane / wing / station / TED:** `NotFoundError` → **404**.
- **Segment write to the terminal station:** `ValidationError` → **422**
  (`wing_service.py:151-156`).
- **Non-unity `differential_ratio` on a non-differential role:**
  `ValidationError` → **422**.
- **Non-unity `mix_gain_secondary` on a non-dual role:** → **422**.
- **Partial patch with `role` omitted:** the gate is **skipped entirely** — a
  `flap` can therefore be patched with any other field without tripping the
  check. 🟡 Consequence: a two-step patch (set role to `elevon`, set
  `mix_gain_secondary`, then set role back to `flap`) could leave an
  inconsistent pair. Whether a re-validation on role change exists was not
  captured.
- **Out-of-range mixing value:** rejected by the field constraint → 422.
- **Empty patch body:** rejected by the non-empty-patch validator → 422.
- **Unknown field on a patch:** rejected by `extra="forbid"` → 422.
- **Duplicate control names:** `assert_unique_control_names` raises before any
  AVL geometry is emitted, and the client receives **422** (`Q-WD-9 ①`,
  maintainer-answered). 🟢 Today it is a bare `ValueError`, outside the
  `ServiceException` hierarchy and therefore untranslated by the global handler,
  so every path yields an opaque **500** with the message naming the duplicate
  dropped — the user cannot tell "rename your control surface" from "the server
  is broken". A duplicate name is user-correctable input, so it becomes a
  `ValidationDomainError` → 422 whose message names the colliding control.
- **`role = 'other'`:** neither dual nor differential-capable, so both gates
  reject any non-unity mixing value on it.
- **Servo present as `servo_index` rather than `servo_data`:** the `servo`
  property returns the integer. 🟢 **`servo_data` is canonical for new records**
  (`Q-WD-3 ①`); `servo_index` is deprecated and the union stays readable only so
  existing rows resolve.
- **Legacy servo row with a `NULL` dimension:** 🟢 **rejected on read, not
  silently defaulted** (`Q-WD-3 ②`). Substituting a plausible number for a
  missing servo dimension would put an invented value into a CAD build — the
  undeclared substitution ADR 0020 forbids. The error names the row and the
  field so it can be filled in.

## Dependencies

- **`avl-integration`** — consumes the resolved axes, signs, gains and names to
  write `CONTROL` lines into the `.avl` file. The uniqueness assertion exists
  entirely for its benefit.
- **`aero-analysis` (AeroSandbox builder, trim, retrim, stability)** — consumes
  the same decomposition, and its three services are **required to obtain names
  through this use case's resolver** (`Q-WD-1`). 🟢 They currently key on the raw
  DB TED name (open bug #955); the resolver removes that possibility.
- **[`../cross-section-crud/`](../cross-section-crud/design.md)** — owns the
  station addressing, the terminal-station guard, and the converter that
  overwrites the x-sec control surface with the TED-derived one.
- **`app/converters/model_schema_converters.py`** — `_build_segment_details`
  and `_merge_ted_with_control_surface`.
- **`components` / `Component`** — the servo's `component_id` points at the
  library part it was picked from.
- **`cad_designer` topology (`TrailingEdgeDevice`)** — the mm-world CAD
  representation and the source of the 25° / `"top"` / `1.0` defaults;
  **read-only** (ADR 0002).
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A role is decomposed into axes in **one** module shared by the AVL builder, the ASB builder and trim enrichment, rather than each deriving its own | `control_surface_mixing.py` module docstring; ADR 0008 | 🟢 |
| A dual-role surface is modelled as **two** AVL `CONTROL` variables on one section, exploiting AVL's per-section summation, rather than as a single blended deflection | `control_surface_mixing.py:126-128` (gh-772) | 🟢 |
| The secondary axis baseline is pinned to `0.0` specifically to protect the AeroBuildup fallback path | `control_surface_mixing.py:126-128` | 🟢 |
| Single-axis roles are passed through byte-for-byte, making gh-772 a strictly additive change | `control_surface_mixing.py:134-146` | 🟢 |
| Uniqueness is an **assertion that raises**, not a rename or a dedupe, because a silent AVL collapse is worse than a hard failure | `control_surface_mixing.py:149-164` | 🟢 |
| The role is embedded in the control name (`[role]axis_wing_index`) so an `.avl` file is self-describing | `control_surface_mixing.py:76-84` | 🟢 |
| `differential_ratio` is deliberately excluded from the physics and applied post-trim for display only | `control_surface_mixing.py:14-15`; `aeroplaneschema.py:372-381` | 🟢 |
| Mixing legality is enforced by **role gating** in the schema rather than by separate per-role schemas | `_validate_mix_fields:51-78` | 🟢 |
| The gate is skipped when `role` is `None`, trading strictness for partial-patch ergonomics | `_validate_mix_fields:51-78` | 🟢 (the trade-off is 🟡) |
| Float comparison uses `math.isclose` rather than `==`, tolerating JSON round-trip drift | `_validate_mix_fields:51-78` | 🟢 |
| `control_surface` is a computed projection, not a stored duplicate, so TED and projection cannot drift | `aeroplanemodel.py:241-276` | 🟢 |
| Servo dimensions are validated in Pydantic while the columns stay nullable ("validate above the topology layer") | `app/schemas/Servo.py:6-13` vs nullable columns; ADR 0002 | 🟡 |

## Internal State

Stateless between requests. The decomposition itself is a **pure function** of
`(role, deflection_deg, mix_gain_primary, mix_gain_secondary, wing_key,
xsec_index)` — no session, no cache.

Persistent state:

- `wing_xsec_trailing_edge_devices` — the single stored source of the surface.
- `wing_xsec_ted_servos` — 1:1 pocket geometry, **millimetres**.

`WingXSecModel.control_surface` is computed on read and never persisted;
`cad_details` and `servo_details` are **subsets of the same TED row**, not
independent storage. 🟢

## Observability

- Validation failures surface as 422 responses with the standard error envelope;
  4xx are logged at INFO by the global handler. 🟢
- `assert_unique_control_names` raises — the failure is loud by design, in
  deliberate contrast to AVL's silence. 🟢
- No metrics, traces or structured events are emitted by this use case. 🟢
- 🟢 **The #955 fallback is removed rather than reported** (`Q-WD-1`). The
  question of whether a silent ±25° substitution should raise a design warning
  dissolves: there is no substitution left to warn about, because the consumers
  resolve the canonical name instead of guessing. This is the stronger form of
  the ADR 0020 rule — remove the undeclared fallback, do not merely declare it.

## Risks and Gaps

- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): this
  use case owns a resolver that trim, retrim and stability are **required** to
  call, and the hard-coded ±25° fallback is removed.
- 🟢 **A duplicate control name returns 422** (`Q-WD-9 ①`), not the opaque 500 it
  produces today. `required_section_modulus` was checked in the same pass and is
  **unreachable in production** — its only caller validates first with a real
  `ValidationError` → 422 — so it is confirmed safe rather than a second defect.
- 🟢 **`servo_data` is canonical for new records; `servo_index` is deprecated**
  (`Q-WD-3 ①`). The union stays readable, but a consumer no longer has to
  type-switch for anything newly written.
- 🟢 **A `NULL` servo dimension is rejected on read** (`Q-WD-3 ②`) rather than
  defaulted — an invented dimension would reach a CAD build.
- 🟢 **The topology classes are the single authority for defaults**
  (`Q-WD-3 ③`, ADR 0022). `NULL` in the DB means *"not stated"*; the effective
  value comes from `TrailingEdgeDevice` at build time, and the DB must **not**
  acquire a second set of defaults — two sets would diverge silently on any
  edit. The confusion with the #955 fallback disappears with the fallback
  itself: 25° is now only ever the topology default, never a substitution.
- 🟢 **`role` gains a CHECK constraint / enum** (`Q-WD-3 ④`). An unknown role is
  currently treated **silently as single-axis**, so a typo produces a wing that
  builds and flies differently from what was asked, with no error anywhere.
- 🟡 **The `role is None` skip is a validation hole.** A multi-step patch
  sequence can leave a `flap` carrying a non-unity `mix_gain_secondary` if the
  role is changed in a later request without re-validating the existing mixing
  fields. Whether a re-validation on role change exists was not captured.
- 🟡 **`role` has no database-level constraint.** It is a plain `String NOT NULL
  DEFAULT 'other'`; the legal `ControlSurfaceRole` values are enforced only in
  Pydantic, so a direct SQL write can introduce an unknown role that
  `_DUAL_ROLE_AXES` will silently treat as single-axis.
- 🟡 **`deflection_deg` doubles as the primary baseline.** The column is
  documented as the "current commanded deflection" and is also what the primary
  axis baseline reads. Whether a stored non-zero commanded deflection is meant
  to persist into every subsequent trim is not spelled out.
